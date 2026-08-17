"""Herramienta de conversión de monedas con tasas en vivo.

Usa open.er-api.com (gratis, sin API key). El buscador de tasas es inyectable
para testear sin red.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from polo.core.ports.tool import RiskLevel
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.tools.currency")

# Un buscador de tasas recibe la moneda base y devuelve {codigo: tasa} o None.
RatesFetcher = Callable[[str], "dict[str, float] | None"]

# Alias en español -> código ISO (para los más comunes).
_ALIAS = {
    "DOLAR": "USD",
    "DOLARES": "USD",
    "DÓLAR": "USD",
    "DÓLARES": "USD",
    "PESO": "UYU",
    "PESOS": "UYU",  # para un usuario uruguayo, "pesos" = UYU
    "EURO": "EUR",
    "EUROS": "EUR",
    "REAL": "BRL",
    "REALES": "BRL",
}


def _fetch_rates(base: str) -> dict[str, float] | None:
    url = f"https://open.er-api.com/v6/latest/{base}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:  # noqa: S310 - URL fija
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - sin red = no disponible
        log.error("currency_fetch_error", error=str(exc))
        return None
    if data.get("result") != "success":
        return None
    tasas = data.get("rates")
    return {str(k): float(v) for k, v in tasas.items()} if isinstance(tasas, dict) else None


class CurrencyTool:
    """Convierte un monto entre dos monedas con la tasa del día."""

    name = "convertir_moneda"
    description = (
        "Convierte un monto entre monedas con la tasa del día. Usala para "
        "'¿cuánto son 500 dólares en pesos?', 'convertí 100 euros a dólares'. "
        "Argumentos: 'cantidad' (número), 'de' (código o nombre, ej USD/dólares), "
        "'a' (código o nombre, ej UYU/pesos)."
    )
    risk = RiskLevel.SAFE
    final = True

    def __init__(self, fetcher: RatesFetcher | None = None) -> None:
        self._fetch = fetcher or _fetch_rates

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cantidad": {"type": "number", "description": "Monto a convertir."},
                "de": {"type": "string", "description": "Moneda de origen (ej: USD)."},
                "a": {"type": "string", "description": "Moneda de destino (ej: UYU)."},
            },
            "required": ["cantidad", "de", "a"],
        }

    def _codigo(self, valor: str) -> str:
        v = valor.strip().upper()
        return _ALIAS.get(v, v)

    def run(self, arguments: dict[str, Any]) -> str:
        try:
            cantidad = float(arguments.get("cantidad"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return "¿Qué monto querés convertir?"

        de = self._codigo(str(arguments.get("de", "")))
        a = self._codigo(str(arguments.get("a", "")))
        if not de or not a:
            return "Decime desde qué moneda y a cuál (ej: de USD a UYU)."

        tasas = self._fetch(de)
        if tasas is None:
            return f"No pude obtener la cotización de {de} ahora. Probá de nuevo."
        if a not in tasas:
            return f"No conozco la moneda '{a}'. Usá un código ISO (USD, UYU, EUR...)."

        convertido = cantidad * tasas[a]
        return f"{cantidad:g} {de} = {convertido:,.2f} {a} (tasa del día)."
