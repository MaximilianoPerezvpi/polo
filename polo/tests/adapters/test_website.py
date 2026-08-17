"""Tests del abridor de sitios web (sin navegador)."""

from __future__ import annotations

from polo.adapters.tools.website import OpenWebsiteTool


def test_sitio_conocido() -> None:
    abiertas: list[str] = []
    tool = OpenWebsiteTool(opener=abiertas.append)
    tool.run({"sitio": "gmail"})
    assert abiertas == ["https://mail.google.com"]


def test_calendario_por_nombre() -> None:
    abiertas: list[str] = []
    OpenWebsiteTool(opener=abiertas.append).run({"sitio": "calendario"})
    assert "calendar.google.com" in abiertas[0]


def test_url_directa() -> None:
    abiertas: list[str] = []
    OpenWebsiteTool(opener=abiertas.append).run({"sitio": "https://ejemplo.com"})
    assert abiertas == ["https://ejemplo.com"]


def test_dominio_agrega_https() -> None:
    abiertas: list[str] = []
    OpenWebsiteTool(opener=abiertas.append).run({"sitio": "wikipedia.org"})
    assert abiertas == ["https://wikipedia.org"]


def test_desconocido_busca_google() -> None:
    abiertas: list[str] = []
    OpenWebsiteTool(opener=abiertas.append).run({"sitio": "algo que no existe"})
    assert "google.com/search" in abiertas[0]


def test_sin_sitio() -> None:
    tool = OpenWebsiteTool(opener=lambda u: None)
    assert "qué sitio" in tool.run({"sitio": ""}).lower()
