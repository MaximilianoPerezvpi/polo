"""Herramienta de clima (Open-Meteo, gratis y sin API key).

Solo lectura, SAFE. Igual que la búsqueda: la consulta sale de tu máquina.

El "fetch" es inyectable para poder testear el formateo sin depender de la red.
El fetch real geocodifica la ciudad (nombre -> lat/lon) y luego pide el clima.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from polo.core.ports.tool import RiskLevel

# Un fetch recibe el nombre de una ciudad y devuelve un dict con el clima ya
# resuelto, o lanza una excepción si algo falla.
WeatherFetch = Callable[[str], dict[str, Any]]

# Códigos de clima de Open-Meteo (WMO) a descripción en español (los comunes).
_CODIGOS = {
    0: "despejado",
    1: "mayormente despejado",
    2: "parcialmente nublado",
    3: "nublado",
    45: "niebla",
    48: "niebla con escarcha",
    51: "llovizna leve",
    61: "lluvia leve",
    63: "lluvia moderada",
    65: "lluvia fuerte",
    71: "nevada leve",
    80: "chubascos",
    95: "tormenta",
}


def _open_meteo(ciudad: str) -> dict[str, Any]:
    """Fetch real: geocodifica la ciudad y consulta el clima actual."""
    import httpx

    geo = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": ciudad, "count": 1, "language": "es"},
        timeout=10,
    ).json()
    resultados = geo.get("results")
    if not resultados:
        raise ValueError(f"No encontré la ciudad '{ciudad}'.")
    lugar = resultados[0]
    lat, lon = lugar["latitude"], lugar["longitude"]

    clima = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        },
        timeout=10,
    ).json()
    actual = clima["current"]
    return {
        "lugar": lugar.get("name", ciudad),
        "pais": lugar.get("country", ""),
        "temperatura": actual["temperature_2m"],
        "humedad": actual["relative_humidity_2m"],
        "viento": actual["wind_speed_10m"],
        "codigo": actual["weather_code"],
    }


class WeatherTool:
    """Consulta el clima actual de una ciudad."""

    name = "clima"
    description = "Consulta el clima actual de una ciudad. Argumento: 'ciudad'."
    risk = RiskLevel.SAFE

    def __init__(self, fetch: WeatherFetch | None = None) -> None:
        self._fetch = fetch or _open_meteo

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ciudad": {
                    "type": "string",
                    "description": "Nombre de la ciudad.",
                }
            },
            "required": ["ciudad"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        ciudad = str(arguments.get("ciudad", "")).strip()
        if not ciudad:
            return "Error: no se indicó ninguna ciudad."

        try:
            d = self._fetch(ciudad)
        except Exception as exc:  # noqa: BLE001 - la red puede fallar de mil formas
            return f"No pude consultar el clima: {exc}"

        desc = _CODIGOS.get(int(d["codigo"]), "condiciones variables")
        lugar = d["lugar"]
        if d.get("pais"):
            lugar += f", {d['pais']}"
        return (
            f"Clima en {lugar}: {desc}, {d['temperatura']}°C, "
            f"humedad {d['humedad']}%, viento {d['viento']} km/h."
        )
