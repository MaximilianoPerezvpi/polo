"""Test de la ventana de historial: charlas largas no crecen sin límite."""

from __future__ import annotations

from typing import Any

from polo.core.models import LLMResponse, Message, Role, ToolSpec, UserInput
from polo.core.registry import ToolRegistry


class LLMEspia:
    """Registra cuántos mensajes recibió en la última llamada."""

    def __init__(self) -> None:
        self.ultimos_mensajes: list[Message] = []

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        self.ultimos_mensajes = messages
        return LLMResponse(text="ok", tool_calls=[])


class MemoriaVacia:
    def remember(self, text: str) -> None: ...
    def recall(self, query: str, k: int) -> list[Any]:
        return []

    def all(self) -> list[Any]:
        return []

    def clear(self) -> None: ...


def _orq(llm: Any, window: int) -> Any:
    from polo.core.orchestrator import Orchestrator

    return Orchestrator(
        llm=llm,
        memory=MemoriaVacia(),
        tools=ToolRegistry(tools=[]),
        system_prompt="sos POLO",
        auto_extract=False,
        history_window=window,
    )


def test_historial_se_acota() -> None:
    llm = LLMEspia()
    orq = _orq(llm, window=6)

    for i in range(10):
        orq.handle(UserInput(text=f"mensaje {i}"))

    # system + (a lo sumo) 6 mensajes recientes = 7. Sin límite serían 21+.
    assert len(llm.ultimos_mensajes) <= 7
    # El system prompt siempre está primero.
    assert llm.ultimos_mensajes[0].role is Role.SYSTEM
    # El mensaje más reciente está incluido.
    assert any("mensaje 9" in (m.content or "") for m in llm.ultimos_mensajes)


def test_sin_limite_si_window_cero() -> None:
    llm = LLMEspia()
    orq = _orq(llm, window=0)
    for i in range(5):
        orq.handle(UserInput(text=f"m{i}"))
    # En la última llamada: system + 4 pares previos (8) + el user actual = 10.
    # (la respuesta del asistente #5 se agrega DESPUÉS de generar.)
    assert len(llm.ultimos_mensajes) == 10
