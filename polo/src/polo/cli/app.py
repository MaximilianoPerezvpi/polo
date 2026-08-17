"""Punto de arranque de POLO por línea de comandos.

Composition root: el ÚNICO lugar donde se arman las piezas concretas. Aquí
decidimos LLM y embeddings = Ollama, memoria = SQLite, interfaz = terminal, y
registramos las herramientas disponibles. El núcleo nunca toma estas decisiones.
"""

from __future__ import annotations

from polo.adapters.speech.kokoro_speaker import KokoroSpeaker
from polo.adapters.speech.nim_speaker import NimSpeaker
from polo.adapters.speech.pyttsx_speaker import PyttsxSpeaker
from polo.adapters.speech.whisper_listener import WhisperMicListener
from polo.bootstrap import build_orchestrator, preflight
from polo.config import Settings, load_settings
from polo.core.errors import LLMUnavailableError
from polo.core.ports.listener import ListenerPort
from polo.core.ports.speech import SpeechPort
from polo.interfaces.cli.chat import CLIChat
from polo.logging_setup import configure_logging, get_logger


def _crear_speaker(settings: Settings) -> SpeechPort | None:
    """Crea el motor de voz con degradación elegante.

    Si se pide kokoro y falla, cae a pyttsx3. Si pyttsx3 falla (p. ej. sin
    audio), devuelve None y POLO sigue en modo texto. Nunca rompe POLO.
    """
    log = get_logger("polo.cli")

    if settings.voice_engine == "nim":
        try:
            return NimSpeaker(
                api_key=settings.nim_api_key,
                voice=settings.nim_tts_voice,
                language=settings.nim_tts_language,
            )
        except Exception as exc:  # noqa: BLE001 - la voz en la nube puede fallar
            log.error("nim_tts_init_failed", error=str(exc))
            # cae a kokoro / pyttsx3

    if settings.voice_engine in {"kokoro", "nim"}:
        try:
            modelo = settings.kokoro_model_path or str(settings.data_dir / "models" / "kokoro.onnx")
            voces = settings.kokoro_voices_path or str(settings.data_dir / "models" / "voices.bin")
            return KokoroSpeaker(
                model_path=modelo,
                voices_path=voces,
                voice=settings.kokoro_voice,
                lang=settings.kokoro_lang,
            )
        except Exception as exc:  # noqa: BLE001 - kokoro puede fallar de varias formas
            log.error("kokoro_init_failed", error=str(exc))
            # cae a pyttsx3

    try:
        return PyttsxSpeaker(rate=settings.voice_rate)
    except Exception as exc:  # noqa: BLE001 - el audio puede fallar de mil formas
        log.error("tts_init_failed", error=str(exc))
        return None


def _crear_listener(settings: Settings) -> ListenerPort | None:
    """Crea la escucha por voz con degradación elegante.

    Si faster-whisper no está instalado o el modelo falla, devuelve None y POLO
    sigue solo con teclado. Nunca rompe POLO.
    """
    log = get_logger("polo.cli")
    try:
        return WhisperMicListener(
            model_size=settings.whisper_model,
            language=settings.stt_language,
            silence_threshold=settings.stt_silence_threshold,
            silence_seconds=settings.stt_silence_seconds,
            start_timeout=settings.stt_start_timeout,
            max_seconds=settings.stt_max_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - STT puede fallar de varias formas
        log.error("stt_init_failed", error=str(exc))
        return None


def main() -> None:
    """Entrada del comando `polo`."""
    settings = load_settings()
    configure_logging(settings.log_level)
    log = get_logger("polo.cli")

    # Voz (Fase 5): motor intercambiable con degradación elegante.
    speaker = _crear_speaker(settings) if settings.voice_output_enabled else None
    listener = _crear_listener(settings) if settings.voice_input_enabled else None

    cli = CLIChat(speaker=speaker, listener=listener)

    # Chequeo de salud: verificamos solo lo que POLO va a usar de verdad.
    try:
        preflight(settings)
    except LLMUnavailableError as exc:
        cli.mostrar_error(str(exc))
        return

    # POLO se construye igual para la CLI y para la GUI (bootstrap compartido).
    # La CLI se pasa a sí misma como confirmer de acciones riesgosas.
    orchestrator = build_orchestrator(settings, cli)

    log.info("polo_conversando", cerebro=settings.llm_backend, voz=speaker is not None)
    cli.saludar()

    # ── Bucle de conversación ─────────────────────────────────────────────
    while True:
        try:
            entrada = cli.receive()
        except (EOFError, KeyboardInterrupt):
            cli.despedir()
            break

        texto = entrada.text.strip()
        bajo = texto.lower()

        if bajo in {"/memoria", "/recuerdos"}:
            cli.mostrar_memoria(orchestrator.memories())
            continue
        if bajo in {"/herramientas", "/tools"}:
            cli.mostrar_herramientas(orchestrator.tool_specs())
            continue
        if bajo == "/olvidar":
            if cli.confirmar("¿Seguro que quieres borrar TODA la memoria?"):
                orchestrator.forget_all()
                cli.error("Memoria borrada.")
            continue

        if cli.es_salida(entrada):
            cli.despedir()
            break

        if not texto:
            continue

        cli.pensando()
        try:
            salida = orchestrator.handle(entrada)
        except LLMUnavailableError as exc:
            cli.error(str(exc))
            continue

        cli.present(salida)


if __name__ == "__main__":
    main()
