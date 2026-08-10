"""Puerto Speech (TTS): convierte texto en voz hablada.

En la Fase 5 lo implementamos con la voz incorporada de Windows (pyttsx3). Más
adelante podríamos cambiar a Piper para una voz más natural, sin tocar nada más:
el núcleo y la interfaz solo conocen este contrato.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SpeechPort(Protocol):
    """Convierte texto en voz y lo reproduce."""

    def speak(self, text: str) -> None:
        """Dice el texto en voz alta (bloquea hasta terminar)."""
        ...
