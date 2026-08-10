"""Tests de la integración memoria + orquestador, con dobles de prueba."""

from __future__ import annotations

from polo.core.models import LLMResponse, MemoryItem, Message, ToolSpec, UserInput
from polo.core.orchestrator import Orchestrator
from polo.core.registry import ToolRegistry

SYSTEM = "Eres POLO."


class MemoriaFalsa:
    def __init__(self) -> None:
        self.items: list[str] = []

    def remember(self, text: str) -> None:
        self.items.append(text)

    def recall(self, query: str, k: int) -> list[MemoryItem]:
        q_words = {w for w in query.lower().split() if len(w) > 3}
        resultados = []
        for t in self.items:
            if t == query:
                resultados.append(MemoryItem(text=t, score=1.0))
            elif q_words & {w for w in t.lower().split() if len(w) > 3}:
                resultados.append(MemoryItem(text=t, score=0.5))
        return resultados[:k]

    def all(self) -> list[MemoryItem]:
        return [MemoryItem(text=t) for t in self.items]

    def clear(self) -> None:
        self.items.clear()


class LLMGuionado:
    """LLM falso: responde según si es turno normal o extracción."""

    def __init__(self, respuesta: str = "ok", extraccion: str = "NADA") -> None:
        self.respuesta = respuesta
        self.extraccion = extraccion
        self.ultimos_mensajes: list[Message] = []

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        self.ultimos_mensajes = list(messages)
        if messages and "extractor de memoria" in messages[0].content:
            return LLMResponse(text=self.extraccion)
        return LLMResponse(text=self.respuesta)


def _orq(llm: LLMGuionado, mem: MemoriaFalsa, auto_extract: bool = True) -> Orchestrator:
    return Orchestrator(
        llm=llm,
        memory=mem,
        tools=ToolRegistry(tools=[]),
        system_prompt=SYSTEM,
        auto_extract=auto_extract,
    )


def test_recorda_que_guarda_explicitamente() -> None:
    mem = MemoriaFalsa()
    orq = _orq(LLMGuionado(), mem, auto_extract=False)

    salida = orq.handle(UserInput(text="recordá que odio el café"))

    assert "odio el café" in mem.items
    assert "recordar" in salida.text.lower()


def test_turno_normal_inyecta_recuerdos_al_modelo() -> None:
    mem = MemoriaFalsa()
    mem.remember("al usuario le gusta el mate")
    llm = LLMGuionado(respuesta="claro")
    orq = _orq(llm, mem, auto_extract=False)

    orq.handle(UserInput(text="gusta algo?"))

    contenidos = " ".join(m.content for m in llm.ultimos_mensajes)
    assert "le gusta el mate" in contenidos


def test_extraccion_automatica_guarda_hechos() -> None:
    mem = MemoriaFalsa()
    llm = LLMGuionado(respuesta="¡hola!", extraccion="El usuario se llama Maxi")
    orq = _orq(llm, mem, auto_extract=True)

    orq.handle(UserInput(text="hola, soy Maxi"))

    assert any("Maxi" in item for item in mem.items)


def test_extraccion_nada_no_guarda() -> None:
    mem = MemoriaFalsa()
    llm = LLMGuionado(respuesta="hola", extraccion="NADA")
    orq = _orq(llm, mem, auto_extract=True)

    orq.handle(UserInput(text="qué hora es"))

    assert mem.items == []


def test_dedup_no_guarda_dos_veces_lo_mismo() -> None:
    mem = MemoriaFalsa()
    orq = _orq(LLMGuionado(), mem, auto_extract=False)

    orq.handle(UserInput(text="recordá que me llamo Maxi"))
    orq.handle(UserInput(text="recordá que me llamo Maxi"))

    assert mem.items.count("me llamo Maxi") == 1
