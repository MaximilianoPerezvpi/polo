"""Tests de las herramientas de automatización (sin lanzar nada real)."""

from __future__ import annotations

from pathlib import Path

from polo.adapters.tools.automation import (
    ListFolderTool,
    MoveFileTool,
    OpenItemTool,
)
from polo.core.ports.tool import RiskLevel

# ── Listar carpeta ─────────────────────────────────────────────────────────


def test_listar_carpeta(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "sub").mkdir()

    resultado = ListFolderTool().run({"ruta": str(tmp_path)})

    assert "a.txt" in resultado
    assert "sub" in resultado


def test_listar_carpeta_inexistente() -> None:
    assert "no existe" in ListFolderTool().run({"ruta": "/no/existe"}).lower()


def test_listar_es_segura() -> None:
    assert ListFolderTool().risk is RiskLevel.SAFE


# ── Abrir ──────────────────────────────────────────────────────────────────


def test_abrir_url_usa_el_opener() -> None:
    abiertos: list[tuple[str, bool]] = []
    tool = OpenItemTool(opener=lambda destino, es_url: abiertos.append((destino, es_url)))

    resultado = tool.run({"destino": "https://ejemplo.com"})

    assert abiertos == [("https://ejemplo.com", True)]
    assert "abrí" in resultado.lower()


def test_abrir_archivo_existente(tmp_path: Path) -> None:
    archivo = tmp_path / "doc.txt"
    archivo.write_text("x")
    abiertos: list[str] = []
    tool = OpenItemTool(opener=lambda destino, es_url: abiertos.append(destino))

    tool.run({"destino": str(archivo)})

    assert abiertos == [str(archivo)]


def test_abrir_bloquea_ejecutables(tmp_path: Path) -> None:
    exe = tmp_path / "virus.exe"
    exe.write_text("x")
    abiertos: list[str] = []
    tool = OpenItemTool(opener=lambda d, u: abiertos.append(d))

    resultado = tool.run({"destino": str(exe)})

    # NO se abrió, y avisa por seguridad.
    assert abiertos == []
    assert "seguridad" in resultado.lower()


def test_abrir_es_confirm() -> None:
    assert OpenItemTool().risk is RiskLevel.CONFIRM


# ── Mover archivo ──────────────────────────────────────────────────────────


def test_mover_archivo(tmp_path: Path) -> None:
    origen = tmp_path / "a.txt"
    origen.write_text("contenido")
    destino = tmp_path / "b.txt"

    resultado = MoveFileTool().run({"origen": str(origen), "destino": str(destino)})

    assert not origen.exists()
    assert destino.read_text() == "contenido"
    assert "moví" in resultado.lower()


def test_mover_no_sobrescribe(tmp_path: Path) -> None:
    origen = tmp_path / "a.txt"
    origen.write_text("nuevo")
    destino = tmp_path / "b.txt"
    destino.write_text("existente")

    resultado = MoveFileTool().run({"origen": str(origen), "destino": str(destino)})

    # No sobrescribe: el destino queda intacto y el origen sigue existiendo.
    assert destino.read_text() == "existente"
    assert origen.exists()
    assert "sobrescribo" in resultado.lower()


def test_mover_origen_inexistente(tmp_path: Path) -> None:
    resultado = MoveFileTool().run({"origen": "/no/existe.txt", "destino": str(tmp_path / "b.txt")})
    assert "no existe" in resultado.lower()


def test_mover_es_confirm() -> None:
    assert MoveFileTool().risk is RiskLevel.CONFIRM
