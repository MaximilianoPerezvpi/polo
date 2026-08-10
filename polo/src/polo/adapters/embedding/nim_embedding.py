"""Adaptador de embeddings en la nube (NVIDIA NIM, compatible con OpenAI).

Implementa el MISMO puerto EmbeddingPort que Ollama. Mover los embeddings a la
nube saca el "peaje local" de cada mensaje (POLO ya no genera vectores en tu
CPU), dejándolo rápido de punta a punta.

Ojo: si cambiás de modelo de embeddings, los recuerdos viejos quedan en otra
dimensión; la memoria los ignora en vez de romperse (ver SqliteMemory).
"""

from __future__ import annotations

from typing import Any

import openai

from polo.core.errors import LLMUnavailableError
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.embedding.nim")


class NimEmbedder:
    """Implementa EmbeddingPort contra un endpoint OpenAI-compatible (NIM)."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        client: Any = None,
    ) -> None:
        self._model = model
        self._client = client or openai.OpenAI(api_key=api_key, base_url=base_url)

    def embed(self, text: str) -> list[float]:
        try:
            resp = self._client.embeddings.create(
                model=self._model,
                input=text,
                # Muchos modelos de retrieval de NIM son "asimétricos" y exigen
                # saber si el texto es consulta o pasaje. Usamos 'query': POLO
                # guarda y busca frases cortas, no documentos largos.
                extra_body={"input_type": "query", "truncate": "END"},
            )
        except openai.AuthenticationError as exc:
            log.error("nim_embed_auth_error", error=str(exc))
            raise LLMUnavailableError(
                "Tu API key de NVIDIA (NIM) parece inválida para embeddings."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - cualquier fallo = no disponible
            log.error("nim_embed_error", error=str(exc))
            raise LLMUnavailableError(
                f"No pude generar embeddings con NIM (modelo '{self._model}')."
            ) from exc
        return [float(x) for x in resp.data[0].embedding]

    def health_check(self) -> None:
        """Verifica que el modelo de embeddings responda (gasta 1 llamada)."""
        self.embed("hola")
