"""El orquestador: el cerebro de POLO.

Fase 3: además de conversar y recordar, ahora puede USAR HERRAMIENTAS.

El loop de herramientas en cada turno normal:
1. Le ofrece al modelo las herramientas disponibles.
2. Si el modelo pide usar una o más, el registro las ejecuta (con permisos).
3. Los resultados vuelven al modelo, que puede pedir más o dar la respuesta final.
4. Repetimos hasta la respuesta final (con un tope de vueltas por seguridad).

El modelo nunca ejecuta nada: solo pide. El registro decide y ejecuta. El núcleo
sigue hablando solo con puertos (LLMPort, MemoryPort, y el ToolRegistry, que a su
vez usa el puerto Tool).
"""

from __future__ import annotations

from polo.core.errors import PoloError
from polo.core.models import (
    AssistantOutput,
    MemoryItem,
    Message,
    Role,
    UserInput,
)
from polo.core.ports.llm import LLMPort
from polo.core.ports.memory import MemoryPort
from polo.core.registry import ToolRegistry

_EXPLICIT_PREFIXES = (
    "recordá que",
    "recorda que",
    "acordate que",
    "acordáte que",
    "recuerda que",
)

_DEDUP_THRESHOLD = 0.90

# Tope de vueltas del loop de herramientas, para que no se cicle infinitamente.
_MAX_TOOL_ITERATIONS = 5

_EXTRACT_INSTRUCTIONS = (
    "Sos un extractor de memoria. Lee el intercambio y extrae hechos duraderos "
    "sobre el USUARIO que valga la pena recordar (nombre, gustos, datos "
    "personales, trabajo, decisiones, objetivos).\n"
    "Reglas:\n"
    "- Un hecho por línea, en tercera persona, breve.\n"
    "- Ignora saludos y charla trivial.\n"
    "- Si no hay nada que recordar, responde exactamente: NADA\n"
    "- No expliques nada. Solo la lista de hechos, o NADA.\n\n"
    "Ejemplos:\n\n"
    "Intercambio:\n"
    "Usuario: hola soy Maxi y me gusta el helado\n"
    "Asistente: ¡Hola Maxi!\n"
    "Hechos:\n"
    "El usuario se llama Maxi\n"
    "Al usuario le gusta el helado\n\n"
    "Intercambio:\n"
    "Usuario: qué hora es?\n"
    "Asistente: Son las 15:00.\n"
    "Hechos:\n"
    "NADA\n\n"
    "Intercambio:\n"
    "Usuario: trabajo como electricista en Montevideo\n"
    "Asistente: Interesante.\n"
    "Hechos:\n"
    "El usuario trabaja como electricista\n"
    "El usuario vive en Montevideo"
)


class Orchestrator:
    """Coordina conversación, memoria y herramientas."""

    def __init__(
        self,
        llm: LLMPort,
        memory: MemoryPort,
        tools: ToolRegistry,
        system_prompt: str,
        recall_k: int = 5,
        auto_extract: bool = True,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._tools = tools
        self._recall_k = recall_k
        self._auto_extract = auto_extract
        self._history: list[Message] = [Message(role=Role.SYSTEM, content=system_prompt)]

    def handle(self, user_input: UserInput) -> AssistantOutput:
        """Procesa un turno completo: memoria + herramientas + conversación."""
        text = user_input.text.strip()

        # 1. Guardado explícito de memoria.
        fact = self._explicit_fact(text)
        if fact is not None:
            self._store_if_new(fact)
            ack = AssistantOutput(text="Anotado. Lo voy a recordar. 🧠")
            self._history.append(Message(role=Role.USER, content=text))
            self._history.append(Message(role=Role.ASSISTANT, content=ack.text))
            return ack

        # 2. Turno normal: recuperamos memoria y corremos el loop de herramientas.
        self._history.append(Message(role=Role.USER, content=text))
        recalled = self._memory.recall(text, self._recall_k)
        answer = self._converse_with_tools(recalled)
        self._history.append(Message(role=Role.ASSISTANT, content=answer))

        # 3. Extracción automática de memoria.
        if self._auto_extract:
            self._extract_and_store(user_text=text, assistant_text=answer)

        return AssistantOutput(text=answer)

    # ── Loop de herramientas ──────────────────────────────────────────────

    def _converse_with_tools(self, recalled: list[MemoryItem]) -> str:
        """Conversa dejando que el modelo use herramientas hasta responder."""
        specs = self._tools.specs()
        # Mensajes de esta ronda: base + turnos de herramientas temporales.
        working: list[Message] = self._build_payload(recalled)

        for _ in range(_MAX_TOOL_ITERATIONS):
            response = self._llm.generate(working, tools=specs)

            if not response.tool_calls:
                return response.text  # respuesta final

            # El modelo pidió herramientas: guardamos su turno y ejecutamos.
            working.append(
                Message(
                    role=Role.ASSISTANT,
                    content=response.text,
                    tool_calls=response.tool_calls,
                )
            )
            for call in response.tool_calls:
                resultado = self._tools.execute(call)
                working.append(Message(role=Role.TOOL, content=resultado, tool_name=call.name))

        return "No pude completar la tarea con las herramientas disponibles."

    # ── Memoria: helpers ──────────────────────────────────────────────────

    def _explicit_fact(self, text: str) -> str | None:
        low = text.lower()
        for prefix in _EXPLICIT_PREFIXES:
            if low.startswith(prefix):
                return text[len(prefix) :].strip(" :,.")
        return None

    def _build_payload(self, recalled: list[MemoryItem]) -> list[Message]:
        payload = [self._history[0]]  # system prompt
        if recalled:
            bloque = "Datos que recordás sobre el usuario (de charlas anteriores):\n"
            bloque += "\n".join(f"- {m.text}" for m in recalled)
            payload.append(Message(role=Role.SYSTEM, content=bloque))
        payload += self._history[1:]
        return payload

    def _store_if_new(self, fact: str) -> None:
        if not fact:
            return
        existing = self._memory.recall(fact, 1)
        if existing and existing[0].score is not None and existing[0].score >= _DEDUP_THRESHOLD:
            return
        self._memory.remember(fact)

    def _extract_and_store(self, user_text: str, assistant_text: str) -> None:
        exchange = f"Intercambio:\nUsuario: {user_text}\nAsistente: {assistant_text}\nHechos:"
        try:
            result = self._llm.generate(
                [
                    Message(role=Role.SYSTEM, content=_EXTRACT_INSTRUCTIONS),
                    Message(role=Role.USER, content=exchange),
                ]
            )
        except PoloError:
            return

        for line in result.text.splitlines():
            hecho = line.strip().lstrip("-•* ").strip()
            if not hecho or hecho.upper().startswith("NADA"):
                continue
            if hecho.lower().rstrip(":") in {"hechos", "intercambio"}:
                continue
            self._store_if_new(hecho)

    # ── Inspección / control ──────────────────────────────────────────────

    def memories(self) -> list[MemoryItem]:
        return self._memory.all()

    def forget_all(self) -> None:
        self._memory.clear()

    @property
    def history(self) -> list[Message]:
        return list(self._history)
