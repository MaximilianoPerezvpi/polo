"""Tests del conversor de monedas (sin red)."""

from __future__ import annotations

from polo.adapters.tools.currency import CurrencyTool


def test_convierte_con_tasa() -> None:
    tool = CurrencyTool(fetcher=lambda base: {"UYU": 40.0, "USD": 1.0})
    resultado = tool.run({"cantidad": 500, "de": "USD", "a": "UYU"})
    assert "20,000.00 UYU" in resultado


def test_alias_en_espanol() -> None:
    # "dólares" -> USD, "pesos" -> UYU
    tool = CurrencyTool(fetcher=lambda base: {"UYU": 40.0})
    resultado = tool.run({"cantidad": 10, "de": "dólares", "a": "pesos"})
    assert "USD" in resultado and "UYU" in resultado


def test_moneda_desconocida() -> None:
    tool = CurrencyTool(fetcher=lambda base: {"UYU": 40.0})
    resultado = tool.run({"cantidad": 10, "de": "USD", "a": "XYZ"})
    assert "no conozco" in resultado.lower()


def test_sin_red() -> None:
    tool = CurrencyTool(fetcher=lambda base: None)
    assert "cotización" in tool.run({"cantidad": 10, "de": "USD", "a": "UYU"}).lower()


def test_cantidad_invalida() -> None:
    tool = CurrencyTool(fetcher=lambda base: {"UYU": 40.0})
    assert "monto" in tool.run({"cantidad": "abc", "de": "USD", "a": "UYU"}).lower()
