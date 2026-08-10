"""Puerto Listener (STT): escucha el micrófono y devuelve texto.

En la Fase 5 (Paso B) lo implementamos con faster-whisper (transcripción local).
La interfaz solo conoce este contrato: si mañana cambiáramos de motor de STT, no
se entera.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ListenerPort(Protocol):
    """Graba del micrófono y devuelve lo que se dijo, como texto."""

    def listen(self) -> str:
        """Graba una intervención y la transcribe (bloquea hasta terminar)."""
        ...
