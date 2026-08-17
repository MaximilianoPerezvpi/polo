"""Herramienta de YouTube: buscar y reproducir un video.

Degradación elegante:
- SIN API key: abre YouTube con la búsqueda (elegís el video con un clic). Cero setup.
- CON API key (gratis, de Google Cloud): busca el primer video y lo abre directo.

Abre el navegador del usuario (webbrowser), sin shell ni inyección. El buscador y
el "abridor" son inyectables para testear sin red ni navegador.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import webbrowser
from collections.abc import Callable
from typing import Any

from polo.core.ports.tool import RiskLevel
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.tools.youtube")

# Un buscador recibe (consulta, api_key) y devuelve el id del video o None.
Searcher = Callable[[str, str], "str | None"]
# Un abridor recibe una URL y la abre.
Opener = Callable[[str], Any]


def _buscar_youtube_api(query: str, api_key: str) -> str | None:
    """Busca el primer video vía la YouTube Data API (solo necesita API key)."""
    params = urllib.parse.urlencode(
        {"part": "snippet", "q": query, "type": "video", "maxResults": 1, "key": api_key}
    )
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:  # noqa: S310 - URL fija de Google
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - si falla, caemos a la búsqueda por navegador
        log.error("youtube_api_error", error=str(exc))
        return None
    items = data.get("items", [])
    if not items:
        return None
    vid = items[0].get("id", {}).get("videoId")
    return str(vid) if vid else None


class YouTubePlayTool:
    """Busca y reproduce un video de YouTube."""

    name = "reproducir_youtube"
    description = (
        "Abre y reproduce un video de YouTube. Pasale qué buscar (tema, canción, "
        "artista, etc.). Usala cuando el usuario diga 'poné en YouTube', 'buscá "
        "un video de', 'reproducí en YouTube'. Argumento: 'consulta'."
    )
    risk = RiskLevel.SAFE
    final = True

    def __init__(
        self, api_key: str = "", opener: Opener | None = None, searcher: Searcher | None = None
    ) -> None:
        self._api_key = api_key
        self._opener = opener or webbrowser.open
        self._searcher = searcher or _buscar_youtube_api

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "consulta": {"type": "string", "description": "Qué video buscar/reproducir."}
            },
            "required": ["consulta"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        consulta = str(arguments.get("consulta", "")).strip()
        if not consulta:
            return "¿Qué video querés que ponga?"

        # Con API key: intentamos reproducir el primer resultado directo.
        if self._api_key:
            video_id = self._searcher(consulta, self._api_key)
            if video_id:
                self._opener(f"https://www.youtube.com/watch?v={video_id}")
                return f"Reproduciendo '{consulta}' en YouTube. ▶️"

        # Sin API key (o sin resultado): abrimos la búsqueda de YouTube.
        q = urllib.parse.quote_plus(consulta)
        self._opener(f"https://www.youtube.com/results?search_query={q}")
        return f"Te abrí YouTube buscando '{consulta}'. ▶️"
