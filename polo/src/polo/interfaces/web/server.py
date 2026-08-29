"""Servidor web de POLO: sirve la GUI futurista y conecta con el cerebro.

Es una interfaz más (como la CLI): usa el mismo `build_orchestrator` compartido.
El núcleo no se entera de que ahora hay una interfaz gráfica.

Voz: si `web_tts=nim`, el servidor genera el audio con Magpie (NVIDIA) y lo manda
al navegador como WAV para que suene esa voz neuronal. Si no, la GUI usa la voz
del navegador. Si Magpie falla, degrada a la voz del navegador (nunca rompe).

Acciones: la GUI aprueba las acciones riesgosas para poder ejecutarlas. Las
protecciones de fondo siguen activas (archivos sensibles bloqueados, sin
sobrescribir, sin ejecutar .exe).
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel

from polo.bootstrap import build_orchestrator, preflight
from polo.config import Settings, load_settings
from polo.core.errors import LLMUnavailableError
from polo.core.models import UserInput
from polo.core.orchestrator import Orchestrator
from polo.logging_setup import configure_logging, get_logger

log = get_logger("polo.web")

_HTML = (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


class TTSProvider(Protocol):
    """Algo que convierte texto en audio WAV (p. ej. NimSpeaker/Magpie)."""

    def synthesize_wav(self, text: str) -> bytes: ...


class _WebConfirmer:
    """Confirmer para la GUI: aprueba las acciones para que POLO pueda ejecutarlas.

    En tu propia máquina y siendo el único usuario, aprobar es razonable (como un
    asistente de voz). Las protecciones de fondo siguen activas: archivos
    sensibles bloqueados, sin sobrescribir al mover, sin ejecutar .exe.
    """

    def confirm(self, prompt: str) -> bool:
        log.info("web_confirm_auto_aprobado", prompt=prompt)
        return True


class ChatIn(BaseModel):
    text: str


def _crear_web_tts(settings: Settings) -> TTSProvider | None:
    """Crea la voz del servidor para la GUI (Magpie), o None si no corresponde."""
    if settings.web_tts != "nim":
        return None
    try:
        from polo.adapters.speech.nim_speaker import NimSpeaker

        return NimSpeaker(
            api_key=settings.nim_api_key,
            voice=settings.nim_tts_voice,
            language=settings.nim_tts_language,
        )
    except Exception as exc:  # noqa: BLE001 - si falla, la GUI usa la voz del navegador
        log.error("web_tts_init_failed", error=str(exc))
        return None


def create_app(
    settings: Settings,
    orchestrator: Orchestrator,
    tts: TTSProvider | None = None,
    task_store: Any = None,
    weather_fetch: Any = None,
) -> Any:
    """Crea la app FastAPI. FastAPI se importa acá para que sea dependencia opcional."""
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="POLO")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _HTML

    @app.get("/api/dashboard")
    def dashboard() -> dict[str, Any]:
        tareas = task_store.list() if task_store is not None else []
        clima = None
        if settings.dashboard_city and weather_fetch is not None:
            try:
                w = weather_fetch(settings.dashboard_city)
                from polo.adapters.tools.weather import _CODIGOS

                clima = {
                    "temp": w["temperatura"],
                    "desc": _CODIGOS.get(w["codigo"], "—"),
                    "lugar": w["lugar"],
                }
            except Exception as exc:  # noqa: BLE001 - sin clima, el panel lo oculta
                log.error("dashboard_weather_error", error=str(exc))
                clima = None
        return {"tasks": tareas, "weather": clima}

    @app.post("/api/chat")
    def chat(msg: ChatIn) -> dict[str, str]:
        # Endpoint síncrono: FastAPI lo corre en un threadpool, así no bloquea.
        try:
            salida = orchestrator.handle(UserInput(text=msg.text))
        except Exception as exc:  # noqa: BLE001 - devolvemos el error a la GUI
            log.error("web_chat_error", error=str(exc))
            return {"error": f"Algo falló: {exc}"}

        respuesta = {"text": salida.text}

        # Voz del servidor (Magpie): si está y funciona, mandamos el audio.
        if tts is not None and salida.text.strip():
            try:
                wav = tts.synthesize_wav(salida.text)
                b64 = base64.b64encode(wav).decode("ascii")
                respuesta["audio"] = f"data:audio/wav;base64,{b64}"
            except Exception as exc:  # noqa: BLE001 - sin audio, la GUI usa su voz
                log.error("web_tts_error", error=str(exc))

        return respuesta

    return app


def run() -> None:
    """Entrada del comando `polo-web`."""
    import sys

    import uvicorn

    # La consola de Windows suele usar una codepage (p. ej. cp1252) que no
    # sabe representar emojis; forzamos UTF-8 para que nunca reviente al
    # imprimir el banner de arranque, incluso sin chcp 65001.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

    settings = load_settings()
    configure_logging(settings.log_level)

    try:
        preflight(settings)
    except LLMUnavailableError as exc:
        print(f"\n  No se pudo iniciar POLO:\n  {exc}\n")
        return

    orchestrator = build_orchestrator(settings, _WebConfirmer())
    tts = _crear_web_tts(settings)

    from polo.adapters.tasks.task_store import TaskStore
    from polo.adapters.tools.weather import _open_meteo

    task_store = TaskStore(settings.data_dir / "tareas.json")
    app = create_app(
        settings, orchestrator, tts=tts, task_store=task_store, weather_fetch=_open_meteo
    )

    voz = "Magpie (servidor)" if tts else "navegador"
    url = "http://127.0.0.1:8000"
    print(f"\n  🟢 POLO web en {url}  ·  voz: {voz}  ·  (Ctrl+C para salir)\n")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
