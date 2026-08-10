"""Punto de arranque de POLO por línea de comandos.

Composition root: el ÚNICO lugar donde se arman las piezas concretas. Aquí
decidimos LLM y embeddings = Ollama, memoria = SQLite, interfaz = terminal, y
registramos las herramientas disponibles. El núcleo nunca toma estas decisiones.
"""

from __future__ import annotations

from typing import Any

from polo.adapters.embedding.nim_embedding import NimEmbedder
from polo.adapters.embedding.ollama_embedding import OllamaEmbedder
from polo.adapters.llm.fallback import FallbackLLM
from polo.adapters.llm.nim_adapter import NimAdapter
from polo.adapters.llm.ollama_adapter import OllamaAdapter
from polo.adapters.memory.sqlite_memory import SqliteMemory
from polo.adapters.plugins.loader import load_plugins
from polo.adapters.speech.kokoro_speaker import KokoroSpeaker
from polo.adapters.speech.pyttsx_speaker import PyttsxSpeaker
from polo.adapters.speech.whisper_listener import WhisperMicListener
from polo.adapters.tools.automation import ListFolderTool, MoveFileTool, OpenItemTool
from polo.adapters.tools.calculator import CalculatorTool
from polo.adapters.tools.clock import ClockTool
from polo.adapters.tools.pc_control import MediaControlTool, OpenAppTool, VolumeTool
from polo.adapters.tools.read_file import ReadFileTool
from polo.adapters.tools.vision_tool import VisionTool
from polo.adapters.tools.weather import WeatherTool
from polo.adapters.tools.web_search import WebSearchTool
from polo.adapters.tools.write_file import WriteFileTool
from polo.adapters.vision.ollama_vision import OllamaVision
from polo.config import Settings, load_settings
from polo.core.errors import LLMUnavailableError
from polo.core.orchestrator import Orchestrator
from polo.core.ports.embedding import EmbeddingPort
from polo.core.ports.listener import ListenerPort
from polo.core.ports.llm import LLMPort
from polo.core.ports.speech import SpeechPort
from polo.core.ports.tool import Tool
from polo.core.registry import ToolRegistry
from polo.interfaces.cli.chat import CLIChat
from polo.logging_setup import configure_logging, get_logger


def _crear_cerebro(settings: Settings, ollama_llm: LLMPort) -> LLMPort:
    """Arma el cerebro de POLO según la config.

    "nim": NVIDIA NIM en la nube como primario, con Ollama local de respaldo si
    la nube falla. "ollama": solo local.
    """
    if settings.llm_backend == "nim":
        nim = NimAdapter(
            model=settings.nim_model,
            api_key=settings.nim_api_key,
            base_url=settings.nim_base_url,
        )
        return FallbackLLM(primary=nim, fallback=ollama_llm)
    return ollama_llm


def _crear_embedder(settings: Settings) -> EmbeddingPort:
    """Elige el generador de embeddings: NIM (nube) u Ollama (local)."""
    if settings.embedding_backend == "nim":
        return NimEmbedder(
            model=settings.nim_embedding_model,
            api_key=settings.nim_api_key,
            base_url=settings.nim_base_url,
        )
    return OllamaEmbedder(
        model=settings.ollama_embedding_model,
        host=settings.ollama_host,
        keep_alive=settings.ollama_keep_alive,
    )


def _preflight(settings: Settings, ollama_llm: Any, embedder: Any) -> None:
    """Verifica solo lo que POLO va a usar según su configuración.

    Chequea el cerebro activo y el embedder activo. Ollama de respaldo es
    best-effort: si no está pero NIM sí, POLO igual arranca.
    """
    # Cerebro
    if settings.llm_backend == "nim":
        NimAdapter(
            model=settings.nim_model,
            api_key=settings.nim_api_key,
            base_url=settings.nim_base_url,
        ).health_check()
    else:
        ollama_llm.health_check(include_self=True)

    # Embeddings
    if settings.embedding_backend == "nim":
        embedder.health_check()
    else:
        ollama_llm.health_check([settings.ollama_embedding_model], include_self=False)


def _crear_speaker(settings: Settings) -> SpeechPort | None:
    """Crea el motor de voz con degradación elegante.

    Si se pide kokoro y falla, cae a pyttsx3. Si pyttsx3 falla (p. ej. sin
    audio), devuelve None y POLO sigue en modo texto. Nunca rompe POLO.
    """
    log = get_logger("polo.cli")

    if settings.voice_engine == "kokoro":
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

    # ── Composition root ──────────────────────────────────────────────────
    ollama_llm = OllamaAdapter(
        model=settings.ollama_model,
        host=settings.ollama_host,
        keep_alive=settings.ollama_keep_alive,
    )
    # Cerebro: NIM en la nube (con Ollama de respaldo) o Ollama local.
    llm: LLMPort = _crear_cerebro(settings, ollama_llm)
    embedder = _crear_embedder(settings)
    memory = SqliteMemory(embedder=embedder, db_path=settings.data_dir / "memory.db")

    # Voz (Fase 5): motor intercambiable con degradación elegante.
    speaker = _crear_speaker(settings) if settings.voice_output_enabled else None
    listener = _crear_listener(settings) if settings.voice_input_enabled else None

    cli = CLIChat(speaker=speaker, listener=listener)

    # Chequeo de salud: verificamos solo lo que POLO va a usar de verdad.
    try:
        _preflight(settings, ollama_llm, embedder)
    except LLMUnavailableError as exc:
        cli.mostrar_error(str(exc))
        return

    # Motor de visión (Fase 6): un modelo multimodal de Ollama.
    vision = OllamaVision(
        model=settings.ollama_vision_model,
        host=settings.ollama_host,
        keep_alive=settings.ollama_keep_alive,
    )

    # Herramientas incorporadas.
    builtin_tools: list[Tool] = [
        ClockTool(),
        CalculatorTool(),
        ReadFileTool(),
        WriteFileTool(workspace=settings.data_dir / "workspace"),
        WebSearchTool(),
        WeatherTool(),
        VisionTool(vision=vision),
    ]

    # Automatización (Fase 7): solo si está habilitada. Las acciones riesgosas
    # (abrir, mover) igual piden confirmación vía el registro.
    if settings.automation_enabled:
        builtin_tools += [
            ListFolderTool(),
            OpenItemTool(),
            MoveFileTool(),
            VolumeTool(),
            OpenAppTool(),
            MediaControlTool(),
        ]

    # Herramientas que aportan los plugins (Fase 4). POLO las descubre solo.
    plugin_tools: list[Tool] = []
    plugins = load_plugins(settings.data_dir / "plugins", enabled=settings.plugins_enabled)
    for p in plugins:
        plugin_tools.extend(p.tools())

    tools = ToolRegistry(tools=builtin_tools + plugin_tools, confirmer=cli)

    orchestrator = Orchestrator(
        llm=llm,
        memory=memory,
        tools=tools,
        system_prompt=settings.system_prompt,
        recall_k=settings.memory_recall_k,
        auto_extract=settings.memory_auto_extract,
    )

    log.info(
        "polo_conversando",
        cerebro=settings.llm_backend,
        modelo=(settings.nim_model if settings.llm_backend == "nim" else settings.ollama_model),
        tools=len(tools),
        plugins=len(plugins),
        voz=speaker is not None,
    )
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
            cli.mostrar_herramientas(tools.specs())
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
