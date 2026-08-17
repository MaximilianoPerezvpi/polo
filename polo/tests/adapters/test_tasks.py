"""Tests del almacén de tareas y sus herramientas."""

from __future__ import annotations

from pathlib import Path

from polo.adapters.tasks.task_store import TaskStore
from polo.adapters.tools.tasks import AddTaskTool, CompleteTaskTool, ListTasksTool


def _store(tmp_path: Path) -> TaskStore:
    return TaskStore(tmp_path / "tareas.json")


def test_store_agregar_y_listar(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add("comprar leche")
    store.add("llamar al dentista")
    assert store.list() == ["comprar leche", "llamar al dentista"]


def test_store_completar(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add("a")
    store.add("b")
    assert store.complete(0) == "a"
    assert store.list() == ["b"]
    assert store.complete(5) is None  # índice inválido


def test_store_persiste(tmp_path: Path) -> None:
    ruta = tmp_path / "tareas.json"
    TaskStore(ruta).add("persistida")
    # Otra instancia (nueva sesión) lee lo mismo del disco.
    assert TaskStore(ruta).list() == ["persistida"]


def test_tool_agregar(tmp_path: Path) -> None:
    store = _store(tmp_path)
    tool = AddTaskTool(store)
    assert "comprar pan" in tool.run({"texto": "comprar pan"})
    assert store.list() == ["comprar pan"]


def test_tool_agregar_vacio(tmp_path: Path) -> None:
    tool = AddTaskTool(_store(tmp_path))
    assert "qué querés" in tool.run({"texto": ""}).lower()


def test_tool_listar_vacio_y_lleno(tmp_path: Path) -> None:
    store = _store(tmp_path)
    tool = ListTasksTool(store)
    assert "no tenés pendientes" in tool.run({}).lower()
    store.add("x")
    assert "1. x" in tool.run({})


def test_tool_completar(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add("tarea1")
    tool = CompleteTaskTool(store)
    assert "tarea1" in tool.run({"numero": 1})
    assert store.list() == []


def test_tool_completar_invalido(tmp_path: Path) -> None:
    tool = CompleteTaskTool(_store(tmp_path))
    assert "no encontré" in tool.run({"numero": 9}).lower()
    assert "número" in tool.run({"numero": "abc"}).lower()
