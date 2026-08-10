"""Tests de la memoria SQLite usando un embedder falso (sin Ollama).

Un embedder falso devuelve vectores conocidos para textos conocidos, así
podemos verificar que la búsqueda por similitud ordena bien, sin depender de
un modelo real.
"""

from __future__ import annotations

from pathlib import Path

from polo.adapters.memory.sqlite_memory import SqliteMemory


class EmbedderFalso:
    """Devuelve vectores fijos según el texto, para tests deterministas."""

    def __init__(self, tabla: dict[str, list[float]]) -> None:
        self.tabla = tabla

    def embed(self, text: str) -> list[float]:
        # Por defecto, un vector "neutro" ortogonal a los de prueba.
        return self.tabla.get(text, [0.0, 0.0, 1.0])


def _memoria(tmp_path: Path, tabla: dict[str, list[float]]) -> SqliteMemory:
    return SqliteMemory(embedder=EmbedderFalso(tabla), db_path=tmp_path / "test_memory.db")


def test_guarda_y_recupera(tmp_path: Path) -> None:
    tabla = {"me gusta el café": [1.0, 0.0, 0.0]}
    mem = _memoria(tmp_path, tabla)

    mem.remember("me gusta el café")

    assert len(mem.all()) == 1
    assert mem.all()[0].text == "me gusta el café"


def test_recall_ordena_por_similitud(tmp_path: Path) -> None:
    # "café" y "cafeína" apuntan casi al mismo lado; "python" al lado opuesto.
    tabla = {
        "me gusta el café": [1.0, 0.0, 0.0],
        "tomo mucha cafeína": [0.9, 0.1, 0.0],
        "programo en python": [0.0, 1.0, 0.0],
        "consulta sobre bebidas": [1.0, 0.05, 0.0],
    }
    mem = _memoria(tmp_path, tabla)
    mem.remember("me gusta el café")
    mem.remember("tomo mucha cafeína")
    mem.remember("programo en python")

    resultados = mem.recall("consulta sobre bebidas", k=3)

    # Los dos primeros deben ser los relacionados con café, no python.
    textos_top2 = {r.text for r in resultados[:2]}
    assert "programo en python" not in textos_top2
    # Y todos traen un score de relevancia.
    assert all(r.score is not None for r in resultados)


def test_recall_vacio_sin_error(tmp_path: Path) -> None:
    mem = _memoria(tmp_path, {})
    assert mem.recall("lo que sea", k=5) == []


def test_clear_borra_todo(tmp_path: Path) -> None:
    tabla = {"un dato": [1.0, 0.0, 0.0]}
    mem = _memoria(tmp_path, tabla)
    mem.remember("un dato")
    assert len(mem.all()) == 1

    mem.clear()
    assert mem.all() == []
