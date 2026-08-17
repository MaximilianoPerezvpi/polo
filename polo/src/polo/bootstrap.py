"""Construcción de POLO compartida entre interfaces (CLI, GUI web, futuras).

Arma el orquestador completo (cerebro, memoria, herramientas, visión) a partir de
la configuración. Cada interfaz le pasa su propio `confirmer` (cómo pedir permiso
para acciones riesgosas) y su forma de mostrar errores.

Vive fuera de cualquier interfaz concreta: la CLI y la web lo usan por igual.
"""

from __future__ import annotations

from polo.adapters.embedding.nim_embedding import NimEmbedder
from polo.adapters.embedding.ollama_embedding import OllamaEmbedder
from polo.adapters.llm.fallback import FallbackLLM
from polo.adapters.llm.nim_adapter import NimAdapter
from polo.adapters.llm.ollama_adapter import OllamaAdapter
from polo.adapters.memory.sqlite_memory import SqliteMemory
from polo.adapters.plugins.loader import load_plugins
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
from polo.config import Settings
from polo.core.orchestrator import Orchestrator
from polo.core.ports.confirm import ConfirmerPort
from polo.core.ports.embedding import EmbeddingPort
from polo.core.ports.llm import LLMPort
from polo.core.ports.tool import Tool
from polo.core.registry import ToolRegistry
from polo.logging_setup import get_logger

log = get_logger("polo.bootstrap")


def crear_cerebro(settings: Settings, ollama_llm: LLMPort) -> LLMPort:
    """Elige el cerebro: NIM en la nube (con respaldo Ollama) o Ollama local."""
    if settings.llm_backend == "nim":
        nim = NimAdapter(
            model=settings.nim_model,
            api_key=settings.nim_api_key,
            base_url=settings.nim_base_url,
        )
        return FallbackLLM(primary=nim, fallback=ollama_llm)
    return ollama_llm


def crear_embedder(settings: Settings) -> EmbeddingPort:
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


def crear_ollama_llm(settings: Settings) -> OllamaAdapter:
    """El adaptador local de Ollama (cerebro local y/o respaldo)."""
    return OllamaAdapter(
        model=settings.ollama_model,
        host=settings.ollama_host,
        keep_alive=settings.ollama_keep_alive,
    )


def preflight(settings: Settings) -> None:
    """Verifica que POLO pueda arrancar (cerebro y embeddings disponibles).

    Lanza LLMUnavailableError con un mensaje claro si algo falta.
    """
    ollama_llm = crear_ollama_llm(settings)
    embedder = crear_embedder(settings)

    if settings.llm_backend == "nim":
        NimAdapter(
            model=settings.nim_model,
            api_key=settings.nim_api_key,
            base_url=settings.nim_base_url,
        ).health_check()
    else:
        ollama_llm.health_check(include_self=True)

    if settings.embedding_backend == "nim":
        embedder.health_check()  # type: ignore[attr-defined]
    else:
        ollama_llm.health_check([settings.ollama_embedding_model], include_self=False)


def build_orchestrator(settings: Settings, confirmer: ConfirmerPort) -> Orchestrator:
    """Arma el orquestador completo listo para usar por cualquier interfaz."""
    ollama_llm = crear_ollama_llm(settings)
    llm = crear_cerebro(settings, ollama_llm)
    embedder = crear_embedder(settings)
    memory = SqliteMemory(embedder=embedder, db_path=settings.data_dir / "memory.db")

    vision = OllamaVision(
        model=settings.ollama_vision_model,
        host=settings.ollama_host,
        keep_alive=settings.ollama_keep_alive,
    )

    builtin_tools: list[Tool] = [
        ClockTool(),
        CalculatorTool(),
        ReadFileTool(),
        WriteFileTool(workspace=settings.data_dir / "workspace"),
        WebSearchTool(),
        WeatherTool(),
        VisionTool(vision=vision),
    ]

    # Tareas/pendientes: sin dependencias ni setup, siempre disponibles.
    from polo.adapters.tasks.task_store import TaskStore
    from polo.adapters.tools.tasks import AddTaskTool, CompleteTaskTool, ListTasksTool

    task_store = TaskStore(settings.data_dir / "tareas.json")
    builtin_tools += [
        AddTaskTool(task_store),
        ListTasksTool(task_store),
        CompleteTaskTool(task_store),
    ]

    # YouTube: sin API key abre la búsqueda; con key reproduce directo.
    from polo.adapters.tools.website import OpenWebsiteTool
    from polo.adapters.tools.youtube import YouTubePlayTool

    builtin_tools.append(YouTubePlayTool(api_key=settings.youtube_api_key))
    builtin_tools.append(OpenWebsiteTool())

    from polo.adapters.tools.currency import CurrencyTool

    builtin_tools.append(CurrencyTool())

    # Resumen del día (usa las tareas y, si hay ciudad, el clima).
    from polo.adapters.tools.briefing import BriefingTool
    from polo.adapters.tools.weather import _open_meteo

    builtin_tools.append(
        BriefingTool(
            task_store=task_store,
            weather_fetch=_open_meteo,
            city=settings.dashboard_city,
        )
    )
    if settings.automation_enabled:
        builtin_tools += [
            ListFolderTool(),
            OpenItemTool(),
            MoveFileTool(),
            VolumeTool(),
            OpenAppTool(),
            MediaControlTool(),
        ]

    plugin_tools: list[Tool] = []
    plugins = load_plugins(settings.data_dir / "plugins", enabled=settings.plugins_enabled)
    for p in plugins:
        plugin_tools.extend(p.tools())

    if settings.spotify_enabled:
        from polo.adapters.tools.spotify import SpotifyPlayTool

        builtin_tools.append(
            SpotifyPlayTool(
                client_id=settings.spotify_client_id,
                client_secret=settings.spotify_client_secret,
                redirect_uri=settings.spotify_redirect_uri,
                cache_path=str(settings.data_dir / ".spotify_cache"),
            )
        )

    tools = ToolRegistry(tools=builtin_tools + plugin_tools, confirmer=confirmer)
    log.info(
        "polo_construido",
        cerebro=settings.llm_backend,
        tools=len(builtin_tools) + len(plugin_tools),
        plugins=len(plugins),
    )

    return Orchestrator(
        llm=llm,
        memory=memory,
        tools=tools,
        system_prompt=settings.system_prompt,
        recall_k=settings.memory_recall_k,
        auto_extract=settings.memory_auto_extract,
        history_window=settings.history_window,
    )
