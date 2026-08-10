"""Tests de humo: lo mínimo para saber que el proyecto está sano."""

from __future__ import annotations

import polo
from polo.config import load_settings


def test_paquete_tiene_version() -> None:
    assert polo.__version__


def test_config_carga_con_valores_por_defecto() -> None:
    settings = load_settings()
    assert settings.log_level  # existe y no está vacío
    assert settings.data_dir.name == ".polo"
