"""Tests del resumen del día (función pura + herramienta)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from polo.adapters.tasks.task_store import TaskStore
from polo.adapters.tools.briefing import BriefingTool, componer_resumen


def test_saludo_segun_hora() -> None:
    manana = componer_resumen([], None, datetime(2026, 8, 12, 8, 0))
    tarde = componer_resumen([], None, datetime(2026, 8, 12, 15, 0))
    noche = componer_resumen([], None, datetime(2026, 8, 12, 22, 0))
    assert "Buenos días" in manana
    assert "Buenas tardes" in tarde
    assert "Buenas noches" in noche


def test_incluye_fecha_y_pendientes() -> None:
    texto = componer_resumen(["estudiar", "llamar"], None, datetime(2026, 8, 12, 9, 0))
    assert "miércoles 12 de agosto" in texto
    assert "2 pendiente" in texto
    assert "estudiar" in texto


def test_sin_pendientes() -> None:
    texto = componer_resumen([], None, datetime(2026, 8, 12, 9, 0))
    assert "No tenés pendientes" in texto


def test_incluye_clima_si_hay() -> None:
    clima = {"temp": 18.4, "desc": "despejado", "lugar": "Montevideo"}
    texto = componer_resumen([], clima, datetime(2026, 8, 12, 9, 0))
    assert "Montevideo" in texto
    assert "18°" in texto


def test_tool_usa_las_tareas(tmp_path: Path) -> None:
    store = TaskStore(tmp_path / "t.json")
    store.add("comprar pan")
    tool = BriefingTool(task_store=store)
    resultado = tool.run({})
    assert "comprar pan" in resultado
