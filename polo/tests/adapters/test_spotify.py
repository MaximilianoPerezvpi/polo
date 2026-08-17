"""Tests de la herramienta de Spotify (con un cliente falso)."""

from __future__ import annotations

from typing import Any

from polo.adapters.tools.spotify import SpotifyPlayTool


class SpotifyFalso:
    def __init__(self, con_dispositivo: bool = True, con_resultados: bool = True) -> None:
        self.con_dispositivo = con_dispositivo
        self.con_resultados = con_resultados
        self.reproducido: list[str] = []

    def search(self, q: str, type: str, limit: int) -> dict[str, Any]:
        if not self.con_resultados:
            return {"tracks": {"items": []}}
        return {
            "tracks": {
                "items": [
                    {
                        "uri": "spotify:track:abc",
                        "name": "Bohemian Rhapsody",
                        "artists": [{"name": "Queen"}],
                    }
                ]
            }
        }

    def devices(self) -> dict[str, Any]:
        if not self.con_dispositivo:
            return {"devices": []}
        return {"devices": [{"id": "dev1", "name": "PC de test", "is_active": True}]}

    def start_playback(self, device_id: str | None = None, uris: list[str] | None = None) -> None:
        self.reproducido = uris or []


def test_reproduce_cancion() -> None:
    cliente = SpotifyFalso()
    tool = SpotifyPlayTool(client=cliente)

    resultado = tool.run({"consulta": "Bohemian Rhapsody"})

    assert "Bohemian Rhapsody" in resultado
    assert "Queen" in resultado
    assert cliente.reproducido == ["spotify:track:abc"]


def test_sin_dispositivo_avisa() -> None:
    tool = SpotifyPlayTool(client=SpotifyFalso(con_dispositivo=False))
    resultado = tool.run({"consulta": "algo"})
    assert "abrí spotify" in resultado.lower() or "abri spotify" in resultado.lower()


def test_sin_resultados_avisa() -> None:
    tool = SpotifyPlayTool(client=SpotifyFalso(con_resultados=False))
    resultado = tool.run({"consulta": "xyzxyz"})
    assert "no encontré" in resultado.lower() or "no encontre" in resultado.lower()


def test_sin_consulta() -> None:
    tool = SpotifyPlayTool(client=SpotifyFalso())
    assert "no me dijiste" in tool.run({"consulta": ""}).lower()
