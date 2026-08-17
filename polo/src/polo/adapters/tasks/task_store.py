"""Almacén simple de tareas/pendientes del usuario (persistido en JSON).

POLO recuerda tus pendientes entre sesiones. Guardado en un archivo JSON (simple
y suficiente para una lista personal), con candado para que la GUI web —que usa
varios hilos— no lo corrompa.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path


class TaskStore:
    """Lista de pendientes persistida en un archivo JSON."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[str]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []
        return [str(x) for x in data] if isinstance(data, list) else []

    def _save(self, tareas: list[str]) -> None:
        self._path.write_text(json.dumps(tareas, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, texto: str) -> None:
        with self._lock:
            tareas = self._load()
            tareas.append(texto)
            self._save(tareas)

    def list(self) -> list[str]:
        with self._lock:
            return self._load()

    def complete(self, index: int) -> str | None:
        """Quita la tarea en la posición dada (0-based). Devuelve su texto o None."""
        with self._lock:
            tareas = self._load()
            if 0 <= index < len(tareas):
                hecha = tareas.pop(index)
                self._save(tareas)
                return hecha
            return None
