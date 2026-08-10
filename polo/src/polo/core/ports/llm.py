"""Puerto LLM: el contrato que debe cumplir cualquier motor de lenguaje.

Fase 3: el contrato creció para soportar herramientas, tal como anticipamos en
la Fase 1. Ahora `generate` recibe opcionalmente las herramientas disponibles y
devuelve un `LLMResponse`, que puede ser texto final o una petición de usar
herramientas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from polo.core.models import LLMResponse, Message, ToolSpec


@runtime_checkable
class LLMPort(Protocol):
    """Genera una respuesta a partir de un historial de mensajes."""

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        """Devuelve la respuesta del modelo: texto o petición de herramientas."""
        ...
