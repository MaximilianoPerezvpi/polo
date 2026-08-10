"""Adaptador de voz con Kokoro (TTS neuronal local, vía ONNX).

Kokoro suena mucho más natural que la voz del sistema (pyttsx3), y tiene voces
en español de verdad. A cambio: hay que descargar un modelo (~300 MB) y, en CPU,
generar la voz agrega algo de latencia.

Implementa el MISMO puerto SpeechPort que pyttsx3, así que se intercambian con
una línea de configuración. El núcleo no se entera de cuál se usa.

El engine y el reproductor son inyectables para poder testear sin audio real.
"""

from __future__ import annotations

import importlib
import os
import tempfile
import wave
from collections.abc import Callable
from typing import Any

import numpy as np

from polo.logging_setup import get_logger

log = get_logger("polo.adapters.speech.kokoro")

# Un reproductor recibe (muestras float32, sample_rate) y las suena.
Player = Callable[[np.ndarray, int], None]


def _reproducir_wav(samples: np.ndarray, sample_rate: int) -> None:
    """Reproduce las muestras escribiendo un WAV temporal y usando winsound."""
    # float32 [-1, 1] -> int16 PCM
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        ruta = tmp.name
    try:
        with wave.open(ruta, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(pcm.tobytes())
        # winsound viene con Windows; lo importamos así para no romper en otros SO.
        winsound = importlib.import_module("winsound")
        winsound.PlaySound(ruta, winsound.SND_FILENAME)
    finally:
        with __import__("contextlib").suppress(OSError):
            os.unlink(ruta)


def _crear_kokoro(model_path: str, voices_path: str) -> Any:
    """Crea el motor Kokoro desde los archivos del modelo."""
    from kokoro_onnx import Kokoro

    return Kokoro(model_path, voices_path)


def _resolver_voz(engine: Any, voz_pedida: str) -> str:
    """Devuelve una voz que exista de verdad en el modelo.

    Si la voz pedida no está (típico: un typo en el .env), usa una voz en
    español disponible en vez de crashear.
    """
    try:
        disponibles = list(engine.voices)
    except Exception:  # noqa: BLE001 - engine falso (tests) o sin .voices: usamos la pedida
        return voz_pedida
    if voz_pedida in disponibles:
        return voz_pedida
    espanolas = [v for v in disponibles if isinstance(v, str) and v.startswith("e")]
    elegida = espanolas[0] if espanolas else (disponibles[0] if disponibles else voz_pedida)
    log.warning("kokoro_voz_no_encontrada", pedida=voz_pedida, usando=elegida)
    return elegida


class KokoroSpeaker:
    """Implementa SpeechPort con la voz neuronal Kokoro."""

    def __init__(
        self,
        model_path: str = "",
        voices_path: str = "",
        voice: str = "ef_dora",
        lang: str = "es",
        speed: float = 1.0,
        engine: Any = None,
        player: Player | None = None,
    ) -> None:
        self._lang = lang
        self._speed = speed
        self._player = player or _reproducir_wav
        # Si no se inyecta engine (uso real), se crea desde los archivos. Si los
        # archivos no están, esto falla y el composition root degrada a pyttsx3.
        self._engine = engine if engine is not None else _crear_kokoro(model_path, voices_path)
        # Validamos la voz al inicio: un typo no debe tumbar POLO al hablar.
        self._voice = _resolver_voz(self._engine, voice)

    def speak(self, text: str) -> None:
        try:
            samples, sample_rate = self._engine.create(
                text, voice=self._voice, speed=self._speed, lang=self._lang
            )
            self._player(samples, sample_rate)
        except Exception as exc:  # noqa: BLE001 - hablar nunca debe tumbar POLO
            log.error("kokoro_speak_error", error=str(exc))
