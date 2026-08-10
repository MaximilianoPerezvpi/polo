"""Cargador de plugins: descubre habilidades desde una carpeta.

Recorre los archivos .py de la carpeta de plugins, los importa, y de cada uno
toma el objeto `PLUGIN`. Si un plugin está roto, lo saltea y sigue (un plugin
malo no debe impedir que POLO arranque).

ADVERTENCIA DE SEGURIDAD: cargar un plugin ejecuta su código con todos los
permisos de Python. Cargá solo plugins en los que confiás (que escribiste vos o
revisaste). No hay sandbox real en esta fase.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import cast

from polo.core.ports.plugin import Plugin
from polo.logging_setup import get_logger

log = get_logger("polo.plugins")


def load_plugins(plugins_dir: Path, enabled: bool = True) -> list[Plugin]:
    """Carga todos los plugins válidos de la carpeta dada."""
    if not enabled:
        return []

    plugins_dir.mkdir(parents=True, exist_ok=True)
    cargados: list[Plugin] = []

    for archivo in sorted(plugins_dir.glob("*.py")):
        if archivo.name.startswith("_"):
            continue  # ignoramos privados/__init__
        try:
            plugin = _load_one(archivo)
        except Exception as exc:  # noqa: BLE001 - un plugin roto no debe tumbar POLO
            log.error("plugin_load_failed", archivo=archivo.name, error=str(exc))
            continue
        cargados.append(plugin)
        log.info("plugin_loaded", nombre=plugin.name, version=plugin.version)

    return cargados


def _load_one(archivo: Path) -> Plugin:
    """Importa un archivo de plugin y devuelve su objeto PLUGIN, validado."""
    spec = importlib.util.spec_from_file_location(f"polo_plugin_{archivo.stem}", archivo)
    if spec is None or spec.loader is None:
        raise ValueError("no se pudo preparar la importación")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    plugin = getattr(module, "PLUGIN", None)
    if plugin is None:
        raise ValueError("el archivo no define un objeto 'PLUGIN'")

    # Validación del contrato con mensajes claros.
    if not (
        hasattr(plugin, "name")
        and hasattr(plugin, "version")
        and callable(getattr(plugin, "tools", None))
    ):
        raise ValueError("'PLUGIN' no cumple el contrato (name, version, tools())")

    return cast(Plugin, plugin)
