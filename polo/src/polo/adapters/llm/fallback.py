"""Cerebro con respaldo: intenta el primario y cae al secundario si falla.

Patrón decorador sobre LLMPort: envuelve dos cerebros (p. ej. NIM en la nube +
Ollama local) y expone el mismo contrato. Si el primario lanza LLMUnavailableError
(nube caída, sin créditos, sin internet), usa el secundario. Así POLO nunca queda
mudo por depender de un solo proveedor.
"""

from __future__ import annotations

from polo.core.errors import LLMUnavailableError
from polo.core.models import LLMResponse, Message, ToolSpec
from polo.core.ports.llm import LLMPort
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.fallback")


class FallbackLLM:
    """Implementa LLMPort probando un primario y cayendo a un secundario."""

    def __init__(self, primary: LLMPort, fallback: LLMPort) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        try:
            return self._primary.generate(messages, tools)
        except LLMUnavailableError as exc:
            log.warning("llm_fallback_a_local", motivo=str(exc))
            return self._fallback.generate(messages, tools)
