"""Tests de la herramienta de YouTube (sin navegador ni red)."""

from __future__ import annotations

from polo.adapters.tools.youtube import YouTubePlayTool


def test_sin_api_key_abre_busqueda() -> None:
    abiertas: list[str] = []
    tool = YouTubePlayTool(api_key="", opener=abiertas.append)

    resultado = tool.run({"consulta": "lofi hip hop"})

    assert len(abiertas) == 1
    assert "youtube.com/results" in abiertas[0]
    assert "lofi" in abiertas[0]
    assert "YouTube" in resultado


def test_con_api_key_reproduce_directo() -> None:
    abiertas: list[str] = []
    tool = YouTubePlayTool(
        api_key="KEY",
        opener=abiertas.append,
        searcher=lambda q, k: "abc123",
    )

    resultado = tool.run({"consulta": "bad bunny"})

    assert abiertas == ["https://www.youtube.com/watch?v=abc123"]
    assert "Reproduciendo" in resultado


def test_api_sin_resultado_cae_a_busqueda() -> None:
    abiertas: list[str] = []
    tool = YouTubePlayTool(
        api_key="KEY",
        opener=abiertas.append,
        searcher=lambda q, k: None,  # la API no encontró nada
    )

    tool.run({"consulta": "algo raro"})

    assert "youtube.com/results" in abiertas[0]  # cayó a la búsqueda


def test_sin_consulta() -> None:
    tool = YouTubePlayTool(opener=lambda u: None)
    assert "qué video" in tool.run({"consulta": ""}).lower()
