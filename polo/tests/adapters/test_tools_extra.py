"""Tests de las herramientas de la ronda extra: archivos, web y clima."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polo.adapters.tools.read_file import ReadFileTool
from polo.adapters.tools.weather import WeatherTool
from polo.adapters.tools.web_search import WebSearchTool
from polo.adapters.tools.write_file import WriteFileTool
from polo.core.ports.tool import RiskLevel

# ── Leer archivos ─────────────────────────────────────────────────────────


def test_leer_archivo_existente(tmp_path: Path) -> None:
    archivo = tmp_path / "nota.txt"
    archivo.write_text("hola mundo", encoding="utf-8")

    resultado = ReadFileTool().run({"ruta": str(archivo)})
    assert "hola mundo" in resultado


def test_leer_archivo_inexistente() -> None:
    resultado = ReadFileTool().run({"ruta": "/no/existe/nada.txt"})
    assert "no existe" in resultado.lower()


# ── Escribir archivos (sandbox) ────────────────────────────────────────────


def test_escribir_archivo_en_workspace(tmp_path: Path) -> None:
    tool = WriteFileTool(workspace=tmp_path / "ws")
    resultado = tool.run({"nombre": "salida.txt", "contenido": "contenido"})

    escrito = tmp_path / "ws" / "salida.txt"
    assert escrito.is_file()
    assert escrito.read_text(encoding="utf-8") == "contenido"
    assert "guardado" in resultado.lower()


def test_escribir_es_riesgosa() -> None:
    assert WriteFileTool(workspace=Path(".")).risk is RiskLevel.CONFIRM


def test_sandbox_bloquea_salir_del_workspace(tmp_path: Path) -> None:
    """Un intento de path traversal debe quedar DENTRO del workspace."""
    ws = tmp_path / "ws"
    tool = WriteFileTool(workspace=ws)

    tool.run({"nombre": "../../hackeado.txt", "contenido": "x"})

    # El archivo NO debe existir fuera del workspace.
    assert not (tmp_path / "hackeado.txt").exists()
    assert not (tmp_path.parent / "hackeado.txt").exists()
    # Debe haber quedado dentro del workspace, con el nombre saneado.
    assert (ws / "hackeado.txt").is_file()


# ── Búsqueda web (backend falso) ───────────────────────────────────────────


def test_busqueda_web_formatea_resultados() -> None:
    def backend_falso(consulta: str, n: int) -> list[dict[str, str]]:
        return [
            {"title": "Título 1", "body": "Resumen 1", "href": "http://a.com"},
            {"title": "Título 2", "body": "Resumen 2", "href": "http://b.com"},
        ]

    tool = WebSearchTool(backend=backend_falso)
    resultado = tool.run({"consulta": "python"})

    assert "Título 1" in resultado
    assert "http://b.com" in resultado


def test_busqueda_web_sin_resultados() -> None:
    tool = WebSearchTool(backend=lambda c, n: [])
    assert "no encontré" in tool.run({"consulta": "xyz"}).lower()


def test_busqueda_web_maneja_error_de_red() -> None:
    def backend_roto(consulta: str, n: int) -> list[dict[str, str]]:
        raise ConnectionError("sin internet")

    tool = WebSearchTool(backend=backend_roto)
    assert "no pude buscar" in tool.run({"consulta": "python"}).lower()


# ── Clima (fetch falso) ────────────────────────────────────────────────────


def test_clima_formatea_bien() -> None:
    def fetch_falso(ciudad: str) -> dict[str, Any]:
        return {
            "lugar": "Montevideo",
            "pais": "Uruguay",
            "temperatura": 18.5,
            "humedad": 70,
            "viento": 12,
            "codigo": 2,
        }

    tool = WeatherTool(fetch=fetch_falso)
    resultado = tool.run({"ciudad": "Montevideo"})

    assert "Montevideo" in resultado
    assert "18.5" in resultado
    assert "parcialmente nublado" in resultado


def test_clima_maneja_error() -> None:
    def fetch_roto(ciudad: str) -> dict[str, Any]:
        raise ValueError("ciudad no encontrada")

    tool = WeatherTool(fetch=fetch_roto)
    assert "no pude consultar" in tool.run({"ciudad": "xyz"}).lower()
