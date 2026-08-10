"""Adaptador de voz con pyttsx3 (voz incorporada del sistema operativo).

En Windows usa SAPI5, que ya trae voces en español (Sabina, Helena) sin
descargar nada.

Detalle importante: pyttsx3 tiene una maña conocida. Si se reusa un mismo motor
de voz para hablar varias veces, a menudo SOLO habla la primera vez y después
queda mudo. La solución confiable es crear un motor FRESCO en cada locución.
Por eso `speak()` crea un engine nuevo cada vez.

El 'engine_factory' es inyectable para poder testear sin audio real.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import Any

from polo.logging_setup import get_logger

log = get_logger("polo.adapters.speech")

# Pistas para reconocer una voz en español entre las del sistema.
_PISTAS_ES = ("spanish", "español", "es-", "es_", "sabina", "helena", "spain")


def _buscar_voz_es(engine: Any) -> str | None:
    """Devuelve el id de una voz en español, si hay alguna instalada."""
    for voz in engine.getProperty("voices"):
        firma = f"{voz.name} {getattr(voz, 'languages', '')} {voz.id}".lower()
        if any(p in firma for p in _PISTAS_ES):
            log.info("voz_es_seleccionada", voz=voz.name)
            return str(voz.id)
    return None


def _crear_engine(rate: int, voice_id: str | None = None) -> Any:
    """Crea un motor de voz nuevo, configurado."""
    import pyttsx3

    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    if voice_id is not None:
        engine.setProperty("voice", voice_id)
    return engine


class PyttsxSpeaker:
    """Implementa SpeechPort con la voz del sistema operativo."""

    def __init__(self, rate: int = 170, engine_factory: Callable[[], Any] | None = None) -> None:
        self._rate = rate
        self._factory = engine_factory
        self._voice_id: str | None = None

        # Si no hay factory (uso real), validamos el audio y resolvemos la voz
        # en español UNA vez, acá. Si el audio no está disponible, esto falla y
        # el composition root degrada a modo texto.
        if engine_factory is None:
            engine = _crear_engine(rate)
            self._voice_id = _buscar_voz_es(engine)
            engine.stop()

    def speak(self, text: str) -> None:
        # Motor FRESCO en cada locución (evita el bug de "solo habla una vez").
        if self._factory is not None:
            engine = self._factory()
        else:
            engine = _crear_engine(self._rate, self._voice_id)
        engine.say(text)
        engine.runAndWait()
        with contextlib.suppress(Exception):
            engine.stop()
