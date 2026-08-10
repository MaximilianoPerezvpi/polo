"""Adaptador de escucha: micrófono + faster-whisper (STT local).

Grabación "hasta que dejás de hablar": presionás Enter, hablás natural, y POLO
corta solo cuando detecta silencio. Más parecido a hablarle a un asistente de
verdad que una ventana fija de segundos.

Cómo funciona la detección: mide el volumen (RMS) de cada trocito de audio. Una
vez que empezaste a hablar, si hay silencio sostenido, corta. Si nunca hablás,
corta por timeout. Un tope máximo evita que grabe para siempre.

El grabador y el transcriptor son inyectables para testear sin hardware ni modelo.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from polo.logging_setup import get_logger

log = get_logger("polo.adapters.speech.whisper")

_SAMPLE_RATE = 16_000  # Whisper espera 16 kHz.
_CHUNK = 0.1  # segundos por trocito que analizamos

# Un grabador devuelve las muestras float32 mono grabadas.
Recorder = Callable[[], "np.ndarray"]
# Un transcriptor convierte muestras en texto.
Transcriber = Callable[["np.ndarray"], str]


def _grabar_hasta_silencio(
    umbral: float, silencio_final: float, timeout_inicio: float, max_segundos: float
) -> np.ndarray:
    """Graba hasta que el usuario deja de hablar (o se alcanza el tope)."""
    import sounddevice as sd

    frames = int(_SAMPLE_RATE * _CHUNK)
    trozos: list[np.ndarray] = []
    hablo = False
    silencio = 0.0
    total = 0.0

    print("🎤 Escuchando... (hablá; corto solo cuando dejes de hablar)")
    with sd.InputStream(
        samplerate=_SAMPLE_RATE, channels=1, dtype="float32", blocksize=frames
    ) as stream:
        while total < max_segundos:
            datos, _ = stream.read(frames)
            trozos.append(np.asarray(datos, dtype=np.float32).copy())
            total += _CHUNK

            rms = float(np.sqrt(np.mean(np.square(datos))))
            if rms >= umbral:
                hablo = True
                silencio = 0.0
            else:
                silencio += _CHUNK
                # Ya habló y se calló un rato -> terminó.
                if hablo and silencio >= silencio_final:
                    break
                # Nunca empezó a hablar -> timeout.
                if not hablo and total >= timeout_inicio:
                    break

    if not hablo:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(trozos, axis=0).flatten()


class WhisperMicListener:
    """Implementa ListenerPort con micrófono + faster-whisper."""

    def __init__(
        self,
        model_size: str = "base",
        language: str = "es",
        silence_threshold: float = 0.02,
        silence_seconds: float = 1.2,
        start_timeout: float = 4.0,
        max_seconds: float = 20.0,
        recorder: Recorder | None = None,
        transcriber: Transcriber | None = None,
    ) -> None:
        self._language = language
        self._recorder = recorder or (
            lambda: _grabar_hasta_silencio(
                silence_threshold, silence_seconds, start_timeout, max_seconds
            )
        )

        if transcriber is not None:
            self._transcriber = transcriber
        else:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
            self._transcriber = self._transcribir_whisper

    def _transcribir_whisper(self, samples: np.ndarray) -> str:
        # vad_filter descarta tramos sin voz: clave para no alucinar con silencio.
        segmentos, _ = self._model.transcribe(samples, language=self._language, vad_filter=True)
        return " ".join(seg.text for seg in segmentos)

    def listen(self) -> str:
        samples = self._recorder()
        if samples.size == 0:
            return ""
        texto = self._transcriber(samples).strip()
        log.info("stt_transcripto", chars=len(texto))
        return texto
