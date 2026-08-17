"""Herramientas de tareas/pendientes: agregar, listar y completar.

POLO gestiona tu lista de pendientes por voz o texto. Son acciones "terminales"
(su resultado ya es la respuesta), así que responden rápido sin volver al modelo.
"""

from __future__ import annotations

from typing import Any

from polo.adapters.tasks.task_store import TaskStore
from polo.core.ports.tool import RiskLevel


class AddTaskTool:
    name = "agregar_tarea"
    description = (
        "Agrega una tarea o pendiente a la lista del usuario. Usala cuando el "
        "usuario diga 'anotá', 'recordá que tengo que', 'agregá a mis pendientes'. "
        "Argumento: 'texto' (la tarea)."
    )
    risk = RiskLevel.SAFE
    final = True

    def __init__(self, store: TaskStore) -> None:
        self._store = store

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"texto": {"type": "string", "description": "La tarea a anotar."}},
            "required": ["texto"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        texto = str(arguments.get("texto", "")).strip()
        if not texto:
            return "¿Qué querés que anote?"
        self._store.add(texto)
        return f"Anotado: {texto} ✅"


class ListTasksTool:
    name = "listar_tareas"
    description = (
        "Lista las tareas/pendientes del usuario. Usala cuando pregunte '¿qué "
        "tengo pendiente?', '¿qué tengo que hacer?', 'mostrame mis tareas'."
    )
    risk = RiskLevel.SAFE
    final = True

    def __init__(self, store: TaskStore) -> None:
        self._store = store

    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def run(self, arguments: dict[str, Any]) -> str:
        tareas = self._store.list()
        if not tareas:
            return "No tenés pendientes. 🎉"
        lineas = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(tareas))
        return f"Tus pendientes:\n{lineas}"


class CompleteTaskTool:
    name = "completar_tarea"
    description = (
        "Marca una tarea como completada por su número (el que aparece al "
        "listar). Usala cuando el usuario diga 'completé la 2', 'ya hice la 1', "
        "'borrá la tarea 3'. Argumento: 'numero'."
    )
    risk = RiskLevel.SAFE
    final = True

    def __init__(self, store: TaskStore) -> None:
        self._store = store

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "numero": {"type": "integer", "description": "Número de la tarea a completar."}
            },
            "required": ["numero"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        try:
            idx = int(str(arguments.get("numero", ""))) - 1
        except (TypeError, ValueError):
            return "Decime el número de la tarea a completar."
        hecha = self._store.complete(idx)
        if hecha is None:
            return "No encontré esa tarea. Fijate el número con 'listar tareas'."
        return f"¡Listo! Completé: {hecha} ✅"
