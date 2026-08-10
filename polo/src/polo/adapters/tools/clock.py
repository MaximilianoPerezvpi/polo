"""Herramienta de reloj: devuelve la fecha y hora actual.

La herramienta más simple posible: sin argumentos, sin riesgo, determinista.
Perfecta para probar que el loop de herramientas funciona de punta a punta.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from polo.core.ports.tool import RiskLevel


class ClockTool:
    """Devuelve la fecha y hora local actual."""

    name = "hora_actual"
    description = "Devuelve la fecha y hora actual del sistema. No lleva argumentos."
    risk = RiskLevel.SAFE

    def parameters(self) -> dict[str, Any]:
        # No acepta argumentos: un objeto JSON Schema vacío.
        return {"type": "object", "properties": {}}

    def run(self, arguments: dict[str, Any]) -> str:
        ahora = datetime.now()
        return ahora.strftime("Fecha y hora actual: %Y-%m-%d %H:%M:%S")
