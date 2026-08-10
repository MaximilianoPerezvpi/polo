"""Tests del orquestador (conversación básica) usando dobles de prueba."""

from __future__ import annotations

from polo.core.models import LLMResponse, MemoryItem, Message, Role, ToolSpec, UserInput
from polo.core.orchestrator import Orchestrator
from polo.core.registry import ToolRegistry

SYSTEM_PROMPT = "Eres POLO, un asistente de prueba."


class MemoriaVacia:
    def remember(self, text: str) -> None:
        pass

    def recall(self, query: str, k: int) -> list[MemoryItem]:
        return []

    def all(self) -> list[MemoryItem]:
        return []

    def clear(self) -> None:
        pass


class LLMEspia:
    """LLM falso que memoriza qué mensajes recibió y responde texto fijo."""

    def __init__(self, respuesta: str = "respuesta de prueba") -> None:
        self.respuesta = respuesta
        self.ultimos_mensajes: list[Message] = []

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        self.ultimos_mensajes = list(messages)
        return LLMResponse(text=self.respuesta)


def _orq(llm: LLMEspia) -> Orchestrator:
    return Orchestrator(
        llm=llm,
        memory=MemoriaVacia(),
        tools=ToolRegistry(tools=[]),
        system_prompt=SYSTEM_PROMPT,
        auto_extract=False,
    )


def test_conversacion_arranca_con_el_system_prompt() -> None:
    espia = LLMEspia()
    _orq(espia).handle(UserInput(text="hola"))

    assert espia.ultimos_mensajes[0].role is Role.SYSTEM
    assert espia.ultimos_mensajes[0].content == SYSTEM_PROMPT


def test_handle_devuelve_la_respuesta_del_modelo() -> None:
    espia = LLMEspia(respuesta="hola humano")
    salida = _orq(espia).handle(UserInput(text="hola"))

    assert salida.text == "hola humano"


def test_mantiene_memoria_de_corto_plazo() -> None:
    espia = LLMEspia(respuesta="ok")
    orq = _orq(espia)

    orq.handle(UserInput(text="primer mensaje"))
    orq.handle(UserInput(text="segundo mensaje"))

    roles = [m.role for m in orq.history]
    assert roles == [
        Role.SYSTEM,
        Role.USER,
        Role.ASSISTANT,
        Role.USER,
        Role.ASSISTANT,
    ]


def test_el_segundo_turno_incluye_el_contexto_del_primero() -> None:
    espia = LLMEspia()
    orq = _orq(espia)

    orq.handle(UserInput(text="me llamo Maxi"))
    orq.handle(UserInput(text="¿cómo me llamo?"))

    contenidos = [m.content for m in espia.ultimos_mensajes]
    assert "me llamo Maxi" in contenidos
