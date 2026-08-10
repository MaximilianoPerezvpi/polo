"""Tests de las herramientas concretas."""

from __future__ import annotations

from polo.adapters.tools.calculator import CalculatorTool
from polo.adapters.tools.clock import ClockTool
from polo.core.ports.tool import RiskLevel


def test_calculadora_suma() -> None:
    calc = CalculatorTool()
    assert "= 14" in calc.run({"expresion": "2 + 3 * 4"})


def test_calculadora_parentesis() -> None:
    calc = CalculatorTool()
    assert "= 27" in calc.run({"expresion": "3 * (4 + 5)"})


def test_calculadora_rechaza_codigo_malicioso() -> None:
    """La calculadora NUNCA debe ejecutar código, solo aritmética."""
    calc = CalculatorTool()
    # Un intento de ejecutar código debe fallar de forma segura, sin ejecutarlo.
    resultado = calc.run({"expresion": "__import__('os').system('echo hola')"})
    assert "no pude" in resultado.lower() or "error" in resultado.lower()


def test_calculadora_division_por_cero() -> None:
    calc = CalculatorTool()
    resultado = calc.run({"expresion": "1 / 0"})
    assert "no pude" in resultado.lower()


def test_reloj_devuelve_fecha() -> None:
    reloj = ClockTool()
    resultado = reloj.run({})
    assert "Fecha y hora actual" in resultado


def test_herramientas_son_seguras() -> None:
    # Ambas herramientas iniciales son de solo lectura.
    assert ClockTool().risk is RiskLevel.SAFE
    assert CalculatorTool().risk is RiskLevel.SAFE
