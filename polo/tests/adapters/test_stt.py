"""Tests de la escucha por voz (sin micrófono ni modelo Whisper real)."""

from __future__ import annotations

import numpy as np

from polo.adapters.speech.whisper_listener import WhisperMicListener


def test_listener_graba_y_transcribe() -> None:
    # Grabador falso con audio; transcriptor fijo.
    listener = WhisperMicListener(
        recorder=lambda: np.ones(1600, dtype=np.float32),
        transcriber=lambda samples: "hola polo",
    )
    assert listener.listen() == "hola polo"


def test_listener_sin_audio_no_transcribe() -> None:
    # Audio vacío (no se detectó voz): no debe transcribirse.
    llamado = False

    def transcriptor(samples: np.ndarray) -> str:
        nonlocal llamado
        llamado = True
        return "no debería"

    listener = WhisperMicListener(
        recorder=lambda: np.zeros(0, dtype=np.float32), transcriber=transcriptor
    )
    assert listener.listen() == ""
    assert not llamado
