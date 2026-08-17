"""Adaptador de voz Magpie TTS de NVIDIA (nube, vía Riva).

Genera voz natural (con estilos emocionales) corriendo en las GPUs de NVIDIA,
con la MISMA API key que el cerebro NIM. No frena tu CPU como la voz local.

Implementa el mismo puerto SpeechPort que pyttsx3 y Kokoro: se intercambian por
configuración. El síntesis y el reproductor son inyectables para testear sin red
ni audio real.
"""

from __future__ import annotations

import contextlib
import importlib
import os
import tempfile
import wave
from collections.abc import Callable
from typing import Any

from polo.logging_setup import get_logger

log = get_logger("polo.adapters.speech.nim")

# ID de la función hosteada de Magpie Multilingual en build.nvidia.com.
_FUNCTION_ID_DEFAULT = "877104f7-e885-42b9-8de8-f6e4c6303969"
_SERVER_DEFAULT = "grpc.nvcf.nvidia.com:443"

# Un reproductor recibe (bytes PCM int16, sample_rate) y los suena.
Player = Callable[[bytes, int], None]


def _reproducir_pcm(audio: bytes, sample_rate: int) -> None:
    """Reproduce audio PCM (int16 mono) vía un WAV temporal y winsound."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        ruta = tmp.name
    try:
        with wave.open(ruta, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            w.writeframes(audio)
        winsound = importlib.import_module("winsound")
        winsound.PlaySound(ruta, winsound.SND_FILENAME)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(ruta)


def _crear_synth(api_key: str, function_id: str, server: str) -> Any:
    """Crea el servicio de síntesis de Riva apuntando al endpoint hosteado."""
    import riva.client

    auth = riva.client.Auth(
        uri=server,
        use_ssl=True,
        metadata_args=[
            ["function-id", function_id],
            ["authorization", f"Bearer {api_key}"],
        ],
    )
    return riva.client.SpeechSynthesisService(auth)


class NimSpeaker:
    """Implementa SpeechPort con la voz Magpie TTS de NVIDIA (nube)."""

    def __init__(
        self,
        api_key: str,
        voice: str = "Magpie-Multilingual.ES-US.Isabela",
        language: str = "es-US",
        function_id: str = _FUNCTION_ID_DEFAULT,
        server: str = _SERVER_DEFAULT,
        sample_rate: int = 22_050,
        synth: Any = None,
        player: Player | None = None,
    ) -> None:
        self._voice = voice
        self._language = language
        self._sample_rate = sample_rate
        self._player = player or _reproducir_pcm

        if synth is not None:
            self._synth = synth
            self._encoding = None  # tests: el mock ignora el encoding
        else:
            import riva.client

            self._synth = _crear_synth(api_key, function_id, server)
            self._encoding = riva.client.AudioEncoding.LINEAR_PCM

    def _synthesize_pcm(self, text: str) -> bytes:
        resp = self._synth.synthesize(
            text=text,
            voice_name=self._voice,
            language_code=self._language,
            sample_rate_hz=self._sample_rate,
            encoding=self._encoding,
        )
        return bytes(resp.audio)

    def speak(self, text: str) -> None:
        try:
            self._player(self._synthesize_pcm(text), self._sample_rate)
        except Exception as exc:  # noqa: BLE001 - hablar nunca debe tumbar POLO
            log.error("nim_tts_error", error=str(exc))

    def synthesize_wav(self, text: str) -> bytes:
        """Devuelve el audio como WAV en memoria, para mandarlo al navegador."""
        import io

        pcm = self._synthesize_pcm(text)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self._sample_rate)
            w.writeframes(pcm)
        return buf.getvalue()
