"""Tests de la interfaz web (servidor), con un orquestador falso."""

from __future__ import annotations

from fastapi.testclient import TestClient

from polo.config import Settings
from polo.core.models import AssistantOutput, UserInput
from polo.interfaces.web.server import create_app


class OrquestadorFalso:
    def __init__(self) -> None:
        self.ultimo: str = ""

    def handle(self, user_input: UserInput) -> AssistantOutput:
        self.ultimo = user_input.text
        return AssistantOutput(text=f"eco: {user_input.text}")


def _client(orq: object, tts: object = None, task_store: object = None) -> TestClient:
    app = create_app(Settings(), orq, tts=tts, task_store=task_store)  # type: ignore[arg-type]
    return TestClient(app)


class TareasFalsas:
    def __init__(self, tareas: list[str]) -> None:
        self._t = tareas

    def list(self) -> list[str]:
        return self._t


class TTSFalso:
    def synthesize_wav(self, text: str) -> bytes:
        return b"RIFF____fake-wav"


def test_index_sirve_html() -> None:
    client = _client(OrquestadorFalso())
    r = client.get("/")
    assert r.status_code == 200
    assert "POLO" in r.text
    assert "<html" in r.text.lower()


def test_chat_responde() -> None:
    orq = OrquestadorFalso()
    client = _client(orq)

    r = client.post("/api/chat", json={"text": "hola polo"})

    assert r.status_code == 200
    assert r.json()["text"] == "eco: hola polo"
    assert orq.ultimo == "hola polo"  # el mensaje llegó al orquestador


def test_chat_maneja_error() -> None:
    class OrquestadorRoto:
        def handle(self, user_input: UserInput) -> AssistantOutput:
            raise RuntimeError("boom")

    client = _client(OrquestadorRoto())
    r = client.post("/api/chat", json={"text": "algo"})

    # No debe tirar 500: devuelve el error en el JSON para mostrarlo en la GUI.
    assert r.status_code == 200
    assert "error" in r.json()


def test_chat_incluye_audio_si_hay_tts() -> None:
    # Con un TTS, la respuesta trae el audio en base64 (data URL).
    client = _client(OrquestadorFalso(), tts=TTSFalso())
    r = client.post("/api/chat", json={"text": "hola"})
    data = r.json()
    assert "audio" in data
    assert data["audio"].startswith("data:audio/wav;base64,")


def test_chat_sin_tts_no_trae_audio() -> None:
    # Sin TTS, no hay audio (la GUI usa la voz del navegador).
    client = _client(OrquestadorFalso())
    r = client.post("/api/chat", json={"text": "hola"})
    assert "audio" not in r.json()


def test_chat_audio_falla_no_rompe_texto() -> None:
    # Si el TTS explota, igual devuelve el texto (sin audio).
    class TTSRoto:
        def synthesize_wav(self, text: str) -> bytes:
            raise RuntimeError("sin voz")

    client = _client(OrquestadorFalso(), tts=TTSRoto())
    r = client.post("/api/chat", json={"text": "hola"})
    data = r.json()
    assert data["text"] == "eco: hola"
    assert "audio" not in data


def test_dashboard_devuelve_tareas() -> None:
    client = _client(OrquestadorFalso(), task_store=TareasFalsas(["comprar pan", "estudiar"]))
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    data = r.json()
    assert data["tasks"] == ["comprar pan", "estudiar"]
    assert data["weather"] is None  # sin ciudad configurada


def test_dashboard_sin_tareas() -> None:
    client = _client(OrquestadorFalso(), task_store=TareasFalsas([]))
    r = client.get("/api/dashboard")
    assert r.json()["tasks"] == []
