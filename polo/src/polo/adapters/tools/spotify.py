"""Herramienta de Spotify: buscar y reproducir una canción por voz/texto.

POLO busca el tema que pidas y lo reproduce en tu Spotify (requiere Premium y que
Spotify esté abierto en algún dispositivo). Usa la API oficial de Spotify vía
spotipy, que maneja el login OAuth (lo más engorroso) y cachea el token.

El cliente de Spotify es inyectable: en uso real es spotipy; en los tests le
pasamos uno falso para no depender de la red ni de credenciales.
"""

from __future__ import annotations

from typing import Any, Protocol

from polo.core.ports.tool import RiskLevel
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.tools.spotify")


class SpotifyClient(Protocol):
    """Lo mínimo que necesitamos de un cliente de Spotify (subset de spotipy)."""

    def search(self, q: str, type: str, limit: int) -> dict[str, Any]: ...
    def devices(self) -> dict[str, Any]: ...
    def start_playback(
        self, device_id: str | None = None, uris: list[str] | None = None
    ) -> None: ...


def _crear_cliente(client_id: str, client_secret: str, redirect_uri: str, cache_path: str) -> Any:
    """Crea el cliente real de spotipy con login OAuth (cachea el token)."""
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="user-modify-playback-state user-read-playback-state",
        cache_path=cache_path,
        open_browser=True,
    )
    return spotipy.Spotify(auth_manager=auth)


class SpotifyPlayTool:
    """Busca una canción y la reproduce en Spotify (requiere Premium)."""

    name = "reproducir_spotify"
    description = (
        "Reproduce una canción en Spotify. Pasale el nombre del tema y/o el "
        "artista. Requiere Spotify Premium y que Spotify esté abierto en algún "
        "dispositivo. Argumento: 'consulta' (ej: 'Bohemian Rhapsody Queen')."
    )
    risk = RiskLevel.SAFE  # reproducir música es benigno
    final = True  # el mensaje ya es la respuesta: sin segundo viaje al modelo

    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        redirect_uri: str = "http://127.0.0.1:8888/callback",
        cache_path: str = ".spotify_cache",
        client: SpotifyClient | None = None,
    ) -> None:
        self._id = client_id
        self._secret = client_secret
        self._redirect = redirect_uri
        self._cache = cache_path
        self._client = client  # si es None, se crea perezosamente en run()

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Canción y/o artista a reproducir.",
                }
            },
            "required": ["consulta"],
        }

    def _cliente(self) -> SpotifyClient:
        if self._client is None:
            self._client = _crear_cliente(self._id, self._secret, self._redirect, self._cache)
        return self._client

    def run(self, arguments: dict[str, Any]) -> str:
        consulta = str(arguments.get("consulta", "")).strip()
        if not consulta:
            return "No me dijiste qué canción poner."

        try:
            sp = self._cliente()
            resultados = sp.search(q=consulta, type="track", limit=1)
            items = resultados.get("tracks", {}).get("items", [])
            if not items:
                return f"No encontré ninguna canción para '{consulta}'."

            track = items[0]
            uri = track["uri"]
            nombre = track["name"]
            artista = track["artists"][0]["name"] if track.get("artists") else ""

            # Elegimos explícitamente un dispositivo y reproducimos EN él. Más
            # confiable que dejar que Spotify adivine el "activo".
            device_id, device_name = self._dispositivo(sp)
            if device_id is None:
                return (
                    f"Encontré '{nombre}' de {artista}, pero no hay ningún "
                    "Spotify abierto. Abrí Spotify (y dale play a algo una vez "
                    "para 'despertarlo') y pedímelo de nuevo."
                )

            sp.start_playback(device_id=device_id, uris=[uri])
            return f"Reproduciendo '{nombre}' de {artista} en {device_name}. 🎵"
        except Exception as exc:  # noqa: BLE001 - la API puede fallar de varias formas
            log.error("spotify_error", error=str(exc))
            return (
                "No pude reproducir en Spotify. Revisá que tengas Premium, que "
                "Spotify esté abierto, y que el login haya funcionado."
            )

    def _dispositivo(self, sp: SpotifyClient) -> tuple[str | None, str]:
        data = sp.devices()
        dispositivos = data.get("devices", [])
        if not dispositivos:
            return None, ""
        # Preferimos uno activo; si no, el primero disponible.
        for d in dispositivos:
            if d.get("is_active"):
                return str(d["id"]), str(d.get("name", ""))
        return str(dispositivos[0]["id"]), str(dispositivos[0].get("name", ""))
