"""Configuración central de POLO.

Usamos `pydantic-settings`: la configuración se declara como una clase tipada y
se carga automáticamente desde variables de entorno o un archivo `.env`. Si
falta algo o tiene el tipo equivocado, falla al arrancar con un error claro, en
vez de romperse a mitad de ejecución.

En Fase 0 la config es mínima a propósito. La sección del LLM (host de Ollama,
nombre del modelo) se agrega en la Fase 1, no antes.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes globales de la aplicación."""

    model_config = SettingsConfigDict(
        env_prefix="POLO_",  # las variables se leen como POLO_LOG_LEVEL, etc.
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Nivel de logging: DEBUG, INFO, WARNING, ERROR.
    log_level: str = "INFO"

    # Carpeta donde POLO guardará datos locales (memoria, etc.) en fases futuras.
    data_dir: Path = Path.home() / ".polo"

    # ── LLM (Fase 1) ──────────────────────────────────────────
    # Qué proveedor de modelo usar. Por ahora solo "ollama", pero el diseño
    # permite agregar otros sin tocar el núcleo.
    llm_provider: str = "ollama"

    # Dónde escucha el servidor local de Ollama.
    ollama_host: str = "http://localhost:11434"

    # Qué modelo usar. Cambiar esto (en el .env) es cómo subimos a un 7B
    # el día de mañana, sin tocar una línea de código.
    ollama_model: str = "qwen2.5:3b"

    # La personalidad de POLO. Vive aquí, en configuración, no incrustada en el
    # código: así ajustar su carácter no requiere tocar la lógica.
    system_prompt: str = (
        "Eres POLO, un asistente personal. Respondes en español de forma "
        "clara y directa. Sé CONCISO: respuestas breves, sin rodeos ni "
        "relleno, porque tus respuestas pueden leerse en voz alta. Eres "
        "honesto: si no sabes algo, lo dices. "
        "Tienes herramientas disponibles, pero las usas SOLO cuando la tarea "
        "realmente las necesita. Para saludos, charla o preguntas generales, "
        "respondes normalmente en español, SIN mencionar funciones, JSON ni "
        "herramientas, y sin disculparte por no usarlas."
    )

    # Cuánto tiempo Ollama mantiene el modelo cargado en RAM entre mensajes.
    # Mantenerlo "caliente" evita recargas lentas desde el disco.
    ollama_keep_alive: str = "30m"

    # ── Cerebro en la nube / NIM (opcional) ───────────────────
    # Qué cerebro usa POLO: "ollama" (local) o "nim" (nube NVIDIA, rápido).
    # Con "nim", Ollama queda de respaldo si la nube falla.
    llm_backend: str = "ollama"
    nim_api_key: str = ""
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_model: str = "meta/llama-3.1-70b-instruct"
    # Backend de embeddings: "ollama" (local) o "nim" (nube). Con "nim", POLO no
    # genera vectores en tu CPU -> mucho más rápido por mensaje.
    # OJO: cambiar de modelo deja los recuerdos viejos en otra dimensión (se
    # ignoran). Empezá con memoria limpia si cambiás.
    embedding_backend: str = "ollama"
    nim_embedding_model: str = "nvidia/nv-embedqa-e5-v5"

    # ── Memoria de largo plazo (Fase 2) ───────────────────────
    # Modelo de Ollama para generar embeddings (vectores de significado).
    ollama_embedding_model: str = "nomic-embed-text"

    # Cuántos recuerdos relevantes recuperar en cada turno.
    memory_recall_k: int = 5

    # Si POLO extrae memoria automáticamente tras cada intercambio.
    # Apagado por defecto: en CPU agrega una llamada extra al modelo por turno.
    # Ponlo en true si quieres que POLO aprenda hechos solo (más lento).
    memory_auto_extract: bool = False

    # ── Plugins (Fase 4) ──────────────────────────────────────
    # Si POLO carga plugins desde su carpeta de plugins (~/.polo/plugins).
    # Ponlo en false para desactivarlos por completo.
    plugins_enabled: bool = True

    # ── Voz (Fase 5) ──────────────────────────────────────────
    # Si POLO responde en voz alta además de por texto.
    voice_output_enabled: bool = False
    # Velocidad de la voz (palabras por minuto aprox.) — solo para pyttsx3.
    voice_rate: int = 170
    # Motor de voz: "pyttsx3" (voz del sistema, rápida) o "kokoro" (neuronal,
    # más natural pero más pesada). Intercambiables sin tocar código.
    voice_engine: str = "pyttsx3"
    # Ajustes de Kokoro (solo si voice_engine = "kokoro").
    kokoro_model_path: str = ""  # ruta al archivo .onnx (ver README)
    kokoro_voices_path: str = ""  # ruta al archivo de voces (ver README)
    kokoro_voice: str = "ef_dora"  # voz en español
    kokoro_lang: str = "es"

    # ── Escucha por voz / STT (Fase 5, Paso B) ────────────────
    # Si POLO puede escucharte por micrófono (Enter vacío = grabar).
    voice_input_enabled: bool = False
    # Tamaño del modelo Whisper: "tiny" (rápido), "base", "small" (mejor).
    whisper_model: str = "base"
    stt_language: str = "es"
    # Escucha "hasta que dejás de hablar": corta al detectar silencio.
    # Si te corta antes de tiempo, subí el silencio final; si tu micro capta
    # ruido de fondo, subí el umbral.
    stt_silence_threshold: float = 0.02  # volumen debajo del cual es "silencio"
    stt_silence_seconds: float = 1.2  # cuánto silencio marca el fin de tu frase
    stt_start_timeout: float = 4.0  # si no hablás en este tiempo, cancela
    stt_max_seconds: float = 20.0  # tope máximo de grabación

    # ── Visión (Fase 6) ───────────────────────────────────────
    # Modelo de visión de Ollama. Descárgalo con: ollama pull llava
    # Alternativas: 'moondream' (más rápido/limitado), 'qwen2.5vl' (mejor español).
    ollama_vision_model: str = "llava"

    # ── Automatización (Fase 7) ───────────────────────────────
    # Interruptor maestro: si POLO puede interactuar con tu sistema (abrir, mover,
    # listar). Las acciones riesgosas igual piden confirmación. Ponlo en false
    # para quitarle a POLO toda capacidad de tocar tu sistema.
    automation_enabled: bool = True


def load_settings() -> Settings:
    """Punto único para obtener la configuración de la app."""
    return Settings()
