"""Tests del cargador de plugins."""

from __future__ import annotations

from pathlib import Path

from polo.adapters.plugins.loader import load_plugins

# Un plugin válido, como texto que escribimos a un archivo temporal.
_PLUGIN_VALIDO = """
from typing import Any
from polo.core.ports.tool import RiskLevel


class SaludoTool:
    name = "saludar"
    description = "Saluda."
    risk = RiskLevel.SAFE

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def run(self, arguments: dict[str, Any]) -> str:
        return "hola"


class SaludoPlugin:
    name = "saludo"
    version = "1.0.0"

    def tools(self) -> list[Any]:
        return [SaludoTool()]


PLUGIN = SaludoPlugin()
"""

# Un plugin roto (falla al importar).
_PLUGIN_ROTO = "esto no es python válido ((("

# Un archivo .py sin objeto PLUGIN.
_SIN_PLUGIN = "x = 1"


def test_carga_un_plugin_valido(tmp_path: Path) -> None:
    (tmp_path / "saludo.py").write_text(_PLUGIN_VALIDO, encoding="utf-8")

    plugins = load_plugins(tmp_path)

    assert len(plugins) == 1
    assert plugins[0].name == "saludo"
    assert plugins[0].version == "1.0.0"
    herramientas = plugins[0].tools()
    assert herramientas[0].name == "saludar"


def test_plugin_roto_no_rompe_la_carga(tmp_path: Path) -> None:
    # Un plugin bueno y uno roto conviviendo: el bueno debe cargar igual.
    (tmp_path / "bueno.py").write_text(_PLUGIN_VALIDO, encoding="utf-8")
    (tmp_path / "roto.py").write_text(_PLUGIN_ROTO, encoding="utf-8")

    plugins = load_plugins(tmp_path)

    # Solo carga el bueno; el roto se saltea sin tumbar nada.
    assert len(plugins) == 1
    assert plugins[0].name == "saludo"


def test_archivo_sin_PLUGIN_se_saltea(tmp_path: Path) -> None:
    (tmp_path / "nada.py").write_text(_SIN_PLUGIN, encoding="utf-8")
    assert load_plugins(tmp_path) == []


def test_deshabilitado_no_carga_nada(tmp_path: Path) -> None:
    (tmp_path / "saludo.py").write_text(_PLUGIN_VALIDO, encoding="utf-8")
    assert load_plugins(tmp_path, enabled=False) == []


def test_carpeta_vacia_no_falla(tmp_path: Path) -> None:
    assert load_plugins(tmp_path) == []
