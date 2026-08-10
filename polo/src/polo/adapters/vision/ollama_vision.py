"""Adaptador de visión con un modelo multimodal de Ollama.

Envía la imagen y una pregunta al modelo de visión y devuelve su respuesta.
Único archivo que conoce cómo hablarle a un modelo de visión de Ollama.
"""

from __future__ import annotations

from pathlib import Path

import ollama

from polo.core.errors import LLMUnavailableError
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.vision")


class OllamaVision:
    """Implementa VisionPort usando un modelo de visión local de Ollama."""

    def __init__(
        self,
        model: str = "llava",
        host: str = "http://localhost:11434",
        keep_alive: str = "30m",
    ) -> None:
        self._model = model
        self._client = ollama.Client(host=host)
        self._keep_alive = keep_alive

    def describe(self, image_path: Path, question: str) -> str:
        datos = image_path.read_bytes()
        try:
            response = self._client.chat(
                model=self._model,
                messages=[{"role": "user", "content": question, "images": [datos]}],
                keep_alive=self._keep_alive,
            )
        except ollama.ResponseError as exc:
            log.error("vision_response_error", error=str(exc))
            raise LLMUnavailableError(
                f"El modelo de visión '{self._model}' falló. "
                f"¿Lo descargaste con 'ollama pull {self._model}'?"
            ) from exc
        except (ConnectionError, ollama.RequestError) as exc:
            log.error("vision_connection_error", error=str(exc))
            raise LLMUnavailableError(
                "No pude conectar con Ollama para analizar la imagen."
            ) from exc

        return response.message.content or ""
