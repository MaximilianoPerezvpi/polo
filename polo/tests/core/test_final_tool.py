"""Test del short-circuit: una herramienta terminal responde sin volver al modelo."""

from __future__ import annotations

from typing import Any

from polo.core.models import LLMResponse, Message, ToolCall, ToolSpec
from polo.core.ports.tool import RiskLevel
from polo.core.registry import ToolRegistry


class HerramientaFinal:
    name = "accion"
    description = "una acción"
    risk = RiskLevel.SAFE
    final = True

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def run(self, arguments: dict[str, Any]) -> str:
        return "Acción hecha."


class HerramientaNormal:
    name = "consulta"
    description = "una consulta"
    risk = RiskLevel.SAFE

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def run(self, arguments: dict[str, Any]) -> str:
        return "datos crudos"


def test_registry_is_final() -> None:
    reg = ToolRegistry(tools=[HerramientaFinal(), HerramientaNormal()])
    assert reg.is_final("accion") is True
    assert reg.is_final("consulta") is False
    assert reg.is_final("inexistente") is False


class LLMQueLlamaHerramienta:
    """Primer turno: pide la herramienta. Si lo llaman de nuevo, falla el test."""

    def __init__(self, tool_name: str) -> None:
        self._tool_name = tool_name
        self.llamadas = 0

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        self.llamadas += 1
        if self.llamadas == 1:
            return LLMResponse(text="", tool_calls=[ToolCall(name=self._tool_name, arguments={})])
        # Segundo viaje: solo debería pasar con herramientas NO terminales.
        return LLMResponse(text="respuesta redactada por el modelo", tool_calls=[])


def _orquestador(llm: Any, tool: Any) -> Any:
    from polo.core.orchestrator import Orchestrator

    class MemoriaVacia:
        def remember(self, text: str) -> None: ...
        def recall(self, query: str, k: int) -> list[Any]:
            return []

        def all(self) -> list[Any]:
            return []

        def clear(self) -> None: ...

    return Orchestrator(
        llm=llm,
        memory=MemoriaVacia(),
        tools=ToolRegistry(tools=[tool]),
        system_prompt="sos POLO",
        auto_extract=False,
    )


def test_herramienta_final_no_vuelve_al_modelo() -> None:
    from polo.core.models import UserInput

    llm = LLMQueLlamaHerramienta("accion")
    orq = _orquestador(llm, HerramientaFinal())

    salida = orq.handle(UserInput(text="hacé la acción"))

    assert salida.text == "Acción hecha."  # el resultado de la herramienta, directo
    assert llm.llamadas == 1  # NO hubo segundo viaje al modelo


def test_herramienta_normal_si_vuelve_al_modelo() -> None:
    from polo.core.models import UserInput

    llm = LLMQueLlamaHerramienta("consulta")
    orq = _orquestador(llm, HerramientaNormal())

    salida = orq.handle(UserInput(text="dame datos"))

    assert salida.text == "respuesta redactada por el modelo"
    assert llm.llamadas == 2  # sí hubo segundo viaje (para redactar)
