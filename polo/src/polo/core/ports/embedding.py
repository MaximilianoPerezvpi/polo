"""Puerto de embeddings: convierte texto en un vector de números.

Un "embedding" es una lista de números que representa el significado de un
texto. Textos parecidos dan vectores parecidos, y eso es lo que nos deja
buscar recuerdos "por significado" y no por palabras exactas.

En la Fase 2 lo implementamos con Ollama, pero el núcleo solo conoce este
contrato: si mañana cambiáramos cómo se generan los vectores, no se entera.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingPort(Protocol):
    """Convierte un texto en su vector de significado."""

    def embed(self, text: str) -> list[float]:
        """Devuelve el embedding (vector) del texto dado."""
        ...
