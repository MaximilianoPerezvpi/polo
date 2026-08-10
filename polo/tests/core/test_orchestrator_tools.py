"""Test del loop de herramientas: el orquestador ejecuta lo que el modelo pide."""

from __future__ import annotations

from typing import Any

from polo.core.models import (
    LLMResponse,
    MemoryItem,
    Message,
    ToolCall,
    ToolSpec,
    UserInput,
)
from polo.core.orchestrator import Orchestrator
from polo.core.ports.tool import RiskLevel
from polo.core.registry import ToolRegistry


class MemoriaVacia:
    def remember(self, text: str) -> None:
        pass

    def recall(self, query: str, k: int) -> list[MemoryItem]:
        return []

    def all(self) -> list[MemoryItem]:
        return []

    def clear(self) -> None:
        pass


class HerramientaEco:
    name = "eco"
    description = "Devuelve un texto fijo."
    risk = RiskLevel.SAFE

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def run(self, arguments: dict[str, Any]) -> str:
        return "resultado-de-la-herramienta"


class LLMConHerramienta:
    """Primero pide una herramienta; en la segunda llamada da la respuesta final."""

    def __init__(self) -> None:
        self.llamadas = 0
        self.vio_resultado = False

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        self.llamadas += 1
        if self.llamadas == 1:
            # Pedimos usar la herramienta "eco".
            return LLMResponse(text="", tool_calls=[ToolCall(name="eco")])
        # En la segunda llamada, el resultado de la herramienta está en el historial.
        for m in messages:
            if "resultado-de-la-herramienta" in m.content:
                self.vio_resultado = True
        return LLMResponse(text="La herramienta dijo algo.")


def test_orquestador_ejecuta_herramienta_y_usa_el_resultado() -> None:
    llm = LLMConHerramienta()
    orq = Orchestrator(
        llm=llm,
        memory=MemoriaVacia(),
        tools=ToolRegistry(tools=[HerramientaEco()]),
        system_prompt="Eres POLO.",
        auto_extract=False,
    )

    salida = orq.handle(UserInput(text="usá la herramienta"))

    # Hubo dos llamadas al modelo (pedir herramienta + responder con el resultado).
    assert llm.llamadas == 2
    # El modelo vio el resultado de la herramienta en la segunda llamada.
    assert llm.vio_resultado is True
    assert salida.text == "La herramienta dijo algo."
