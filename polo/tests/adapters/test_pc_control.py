"""Tests del control de PC (sin tocar audio ni lanzar apps reales)."""

from __future__ import annotations

from polo.adapters.tools.pc_control import MediaControlTool, OpenAppTool, VolumeTool
from polo.core.ports.tool import RiskLevel

_VK_UP = 0xAF
_VK_DOWN = 0xAE
_VK_MUTE = 0xAD


# ── Volumen ─────────────────────────────────────────────────────────────────


def test_subir_volumen_presiona_up_n_veces() -> None:
    presionadas: list[int] = []
    tool = VolumeTool(presser=presionadas.append)

    tool.run({"accion": "subir", "cantidad": 3})

    assert presionadas == [_VK_UP, _VK_UP, _VK_UP]


def test_bajar_volumen_usa_down() -> None:
    presionadas: list[int] = []
    VolumeTool(presser=presionadas.append).run({"accion": "bajar", "cantidad": 2})
    assert presionadas == [_VK_DOWN, _VK_DOWN]


def test_silenciar_presiona_mute_una_vez() -> None:
    presionadas: list[int] = []
    VolumeTool(presser=presionadas.append).run({"accion": "silenciar"})
    assert presionadas == [_VK_MUTE]


def test_accion_invalida() -> None:
    tool = VolumeTool(presser=lambda vk: None)
    assert "inválida" in tool.run({"accion": "explotar"}).lower()


def test_volumen_es_seguro() -> None:
    assert VolumeTool().risk is RiskLevel.SAFE


# ── Abrir aplicación ────────────────────────────────────────────────────────


def test_abrir_app_usa_el_launcher() -> None:
    abiertas: list[str] = []
    tool = OpenAppTool(launcher=abiertas.append)

    resultado = tool.run({"nombre": "chrome"})

    assert abiertas == ["chrome"]
    assert "abrí" in resultado.lower()


def test_abrir_app_rechaza_caracteres_peligrosos() -> None:
    abiertas: list[str] = []
    tool = OpenAppTool(launcher=abiertas.append)

    # Un intento de inyección con '&' debe rechazarse sin lanzar nada.
    resultado = tool.run({"nombre": "chrome & del todo"})

    assert abiertas == []
    assert "inválido" in resultado.lower()


def test_abrir_app_es_confirm() -> None:
    assert OpenAppTool().risk is RiskLevel.CONFIRM


# ── Control de música ───────────────────────────────────────────────────────

_VK_PLAY_PAUSE = 0xB3
_VK_NEXT = 0xB0
_VK_PREV = 0xB1


def test_pausar_musica() -> None:
    presionadas: list[int] = []
    MediaControlTool(presser=presionadas.append).run({"accion": "pausar"})
    assert presionadas == [_VK_PLAY_PAUSE]


def test_siguiente_cancion() -> None:
    presionadas: list[int] = []
    MediaControlTool(presser=presionadas.append).run({"accion": "siguiente"})
    assert presionadas == [_VK_NEXT]


def test_cancion_anterior() -> None:
    presionadas: list[int] = []
    MediaControlTool(presser=presionadas.append).run({"accion": "anterior"})
    assert presionadas == [_VK_PREV]


def test_musica_accion_invalida() -> None:
    tool = MediaControlTool(presser=lambda vk: None)
    assert "inválida" in tool.run({"accion": "explotar"}).lower()


def test_musica_es_segura() -> None:
    assert MediaControlTool().risk is RiskLevel.SAFE
