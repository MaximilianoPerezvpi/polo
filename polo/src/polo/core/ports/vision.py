"""Puerto Vision: analiza imágenes y responde en texto.

En la Fase 6 lo implementamos con un modelo de visión local vía Ollama. El
núcleo (y la herramienta que lo usa) solo conocen este contrato: si mañana
cambiáramos el motor de visión, no se enteran.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class VisionPort(Protocol):
    """Analiza una imagen respondiendo una pregunta sobre ella."""

    def describe(self, image_path: Path, question: str) -> str:
        """Mira la imagen y responde la pregunta (o la describe)."""
        ...
