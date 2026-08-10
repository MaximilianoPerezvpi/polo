"""Tests del registro de herramientas: ejecución, errores y confirmación."""

from __future__ import annotations

from typing import Any

from polo.adapters.tools.clock import ClockTool
from polo.core.models import ToolCall
from polo.core.ports.tool import RiskLevel
from polo.core.registry import ToolRegistry


class HerramientaRiesgosa:
    """Herramienta CONFIRM que registra si se ejecutó."""

    name = "borrar_algo"
    description = "Borra algo (peligroso)."
    risk = RiskLevel.CONFIRM

    def __init__(self) -> None:
        self.ejecutada = False

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def run(self, arguments: dict[str, Any]) -> str:
        self.ejecutada = True
        return "borrado"


class ConfirmadorFalso:
    def __init__(self, responde: bool) -> None:
        self.responde = responde

    def confirm(self, prompt: str) -> bool:
        return self.responde


def test_ejecuta_herramienta_segura() -> None:
    reg = ToolRegistry(tools=[ClockTool()])
    resultado = reg.execute(ToolCall(name="hora_actual"))
    assert "Fecha y hora actual" in resultado


def test_herramienta_inexistente_devuelve_error() -> None:
    reg = ToolRegistry(tools=[ClockTool()])
    resultado = reg.execute(ToolCall(name="no_existe"))
    assert "no existe" in resultado.lower()


def test_herramienta_riesgosa_no_se_ejecuta_sin_confirmacion() -> None:
    peligrosa = HerramientaRiesgosa()
    reg = ToolRegistry(tools=[peligrosa], confirmer=ConfirmadorFalso(responde=False))

    resultado = reg.execute(ToolCall(name="borrar_algo"))

    assert peligrosa.ejecutada is False  # NO se ejecutó
    assert "no autorizó" in resultado.lower()


def test_herramienta_riesgosa_se_ejecuta_con_confirmacion() -> None:
    peligrosa = HerramientaRiesgosa()
    reg = ToolRegistry(tools=[peligrosa], confirmer=ConfirmadorFalso(responde=True))

    resultado = reg.execute(ToolCall(name="borrar_algo"))

    assert peligrosa.ejecutada is True
    assert resultado == "borrado"


def test_error_de_herramienta_no_rompe() -> None:
    class HerramientaRota:
        name = "rota"
        description = "Siempre falla."
        risk = RiskLevel.SAFE

        def parameters(self) -> dict[str, Any]:
            return {"type": "object", "properties": {}}

        def run(self, arguments: dict[str, Any]) -> str:
            raise RuntimeError("boom")

    reg = ToolRegistry(tools=[HerramientaRota()])
    resultado = reg.execute(ToolCall(name="rota"))
    # El error se devuelve como texto, no como excepción.
    assert "error al ejecutar" in resultado.lower()
