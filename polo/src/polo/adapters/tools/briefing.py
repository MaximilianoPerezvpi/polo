"""Briefing / resumen del día: saludo, fecha, pendientes y clima.

El compositor es una función pura (determinista) para poder testearlo con una
fecha fija. Lo usan tanto la herramienta (cuando decís "buenos días") como el
endpoint del panel (para saludarte al abrir la GUI).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from polo.adapters.tasks.task_store import TaskStore
from polo.core.ports.tool import RiskLevel

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]


def componer_resumen(tareas: list[str], clima: dict[str, Any] | None, ahora: datetime) -> str:
    """Arma el texto del resumen del día. Función pura (fácil de testear)."""
    if ahora.hour < 12:
        saludo = "Buenos días"
    elif ahora.hour < 20:
        saludo = "Buenas tardes"
    else:
        saludo = "Buenas noches"

    fecha = f"{_DIAS[ahora.weekday()]} {ahora.day} de {_MESES[ahora.month - 1]}"
    partes = [f"{saludo}. Hoy es {fecha}."]

    if clima:
        partes.append(f"Clima en {clima['lugar']}: {round(clima['temp'])}°, {clima['desc']}.")

    if tareas:
        partes.append(f"Tenés {len(tareas)} pendiente(s):")
        partes += [f"• {t}" for t in tareas[:5]]
    else:
        partes.append("No tenés pendientes. 🎉")

    return "\n".join(partes)


class BriefingTool:
    """Da el resumen del día cuando el usuario lo pide."""

    name = "resumen_del_dia"
    description = (
        "Da un resumen del día: saludo, fecha, tus pendientes y el clima. Usala "
        "cuando el usuario diga 'buenos días', 'dame mi resumen', 'resumen del "
        "día', '¿cómo viene el día?', 'ponme al día'."
    )
    risk = RiskLevel.SAFE
    final = True

    def __init__(self, task_store: TaskStore, weather_fetch: Any = None, city: str = "") -> None:
        self._store = task_store
        self._weather_fetch = weather_fetch
        self._city = city

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def _clima(self) -> dict[str, Any] | None:
        if not self._city or self._weather_fetch is None:
            return None
        try:
            from polo.adapters.tools.weather import _CODIGOS

            w = self._weather_fetch(self._city)
            return {
                "temp": w["temperatura"],
                "desc": _CODIGOS.get(w["codigo"], "—"),
                "lugar": w["lugar"],
            }
        except Exception:  # noqa: BLE001 - sin clima igual damos el resumen
            return None

    def run(self, arguments: dict[str, Any]) -> str:
        return componer_resumen(self._store.list(), self._clima(), datetime.now())
