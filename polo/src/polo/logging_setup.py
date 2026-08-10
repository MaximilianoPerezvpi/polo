"""Configuración de logging estructurado con structlog.

¿Por qué logging estructurado desde el día 1? Porque cuando POLO empiece a
ejecutar acciones y automatizaciones (fases futuras), vas a necesitar rastrear
QUÉ pasó y POR QUÉ. Logs con estructura (clave-valor) son mucho más fáciles de
filtrar y entender que texto plano suelto.
"""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Configura structlog para toda la aplicación.

    Llamar UNA vez al arrancar (desde cli/app.py).
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),  # legible para humanos en desarrollo
        ],
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Devuelve un logger para el módulo dado."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
