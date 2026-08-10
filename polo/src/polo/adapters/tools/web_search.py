"""Herramienta de búsqueda web (DuckDuckGo, gratis y sin API key).

Solo lectura, así que es SAFE. OJO de privacidad: la consulta SALE de tu máquina
hacia DuckDuckGo. Es el precio de tener búsqueda web gratis.

El "backend" de búsqueda es inyectable: en producción usa DuckDuckGo; en los
tests le pasamos uno falso para no depender de internet.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from polo.core.ports.tool import RiskLevel

# Un backend recibe (consulta, max_resultados) y devuelve una lista de dicts
# con claves 'title', 'body', 'href'.
SearchBackend = Callable[[str, int], list[dict[str, str]]]


def _duckduckgo(consulta: str, max_resultados: int) -> list[dict[str, str]]:
    """Backend real: busca en DuckDuckGo."""
    from ddgs import DDGS

    with DDGS() as ddgs:
        return [
            {
                "title": str(r.get("title", "")),
                "body": str(r.get("body", "")),
                "href": str(r.get("href", "")),
            }
            for r in ddgs.text(consulta, max_results=max_resultados)
        ]


class WebSearchTool:
    """Busca en la web y devuelve los primeros resultados."""

    name = "buscar_web"
    description = (
        "Busca información actual en internet y devuelve los primeros resultados. "
        "Útil para noticias, datos recientes o cosas que no sabés. "
        "Argumento: 'consulta'."
    )
    risk = RiskLevel.SAFE

    def __init__(self, backend: SearchBackend | None = None, max_resultados: int = 5) -> None:
        self._backend = backend or _duckduckgo
        self._max = max_resultados

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Lo que se quiere buscar.",
                }
            },
            "required": ["consulta"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        consulta = str(arguments.get("consulta", "")).strip()
        if not consulta:
            return "Error: no se indicó qué buscar."

        try:
            resultados = self._backend(consulta, self._max)
        except Exception as exc:  # noqa: BLE001 - la red puede fallar de mil formas
            return f"No pude buscar en la web: {exc}"

        if not resultados:
            return f"No encontré resultados para '{consulta}'."

        lineas = []
        for r in resultados:
            lineas.append(f"• {r['title']}\n  {r['body']}\n  {r['href']}")
        return f"Resultados para '{consulta}':\n\n" + "\n\n".join(lineas)
