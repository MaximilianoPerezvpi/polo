"""Adaptador de embeddings con Ollama.

Reutiliza el mismo Ollama que ya usás para conversar, con un modelo chico
dedicado a generar vectores. Así evitamos librerías pesadas como PyTorch.
"""

from __future__ import annotations

import ollama

from polo.core.errors import LLMUnavailableError
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.embedding")


class OllamaEmbedder:
    """Implementa EmbeddingPort convirtiendo texto en vectores vía Ollama."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        host: str = "http://localhost:11434",
        keep_alive: str = "30m",
    ) -> None:
        self._model = model
        self._client = ollama.Client(host=host)
        self._keep_alive = keep_alive

    def embed(self, text: str) -> list[float]:
        try:
            resp = self._client.embed(model=self._model, input=text, keep_alive=self._keep_alive)
        except ollama.ResponseError as exc:
            log.error("embedding_response_error", error=str(exc))
            raise LLMUnavailableError(
                f"El modelo de embeddings '{self._model}' falló. "
                f"¿Lo descargaste con 'ollama pull {self._model}'?"
            ) from exc
        except (ConnectionError, ollama.RequestError) as exc:
            log.error("embedding_connection_error", error=str(exc))
            raise LLMUnavailableError(
                "No pude conectar con Ollama para generar embeddings."
            ) from exc
        # embed acepta uno o varios textos; pasamos uno, tomamos el primer vector.
        return [float(x) for x in resp.embeddings[0]]
