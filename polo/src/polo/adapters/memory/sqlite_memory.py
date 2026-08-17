"""Memoria de largo plazo: SQLite + búsqueda por similitud con numpy.

Esta es nuestra "base vectorial hecha a mano". En vez de instalar una base
vectorial pesada, guardamos cada recuerdo en SQLite junto a su vector, y para
buscar comparamos vectores con matemática simple (similitud coseno). Para la
cantidad de recuerdos de un solo usuario, esto es instantáneo y totalmente
transparente: podés leer este archivo y entender exactamente cómo funciona la
memoria de POLO.

Implementa MemoryPort. El núcleo no sabe nada de esto.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

import numpy as np

from polo.core.models import MemoryItem
from polo.core.ports.embedding import EmbeddingPort


def _cosine_similarities(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Similitud coseno entre un vector y cada fila de una matriz (0 a 1)."""
    # Normalizamos para que el coseno sea solo el producto punto.
    query_norm = query / (np.linalg.norm(query) + 1e-10)
    matrix_norms = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-10)
    return np.asarray(matrix_norms @ query_norm, dtype=np.float64)


class SqliteMemory:
    """Implementa MemoryPort guardando texto + vector en SQLite."""

    def __init__(self, embedder: EmbeddingPort, db_path: Path) -> None:
        self._embedder = embedder
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: la GUI web atiende cada mensaje en un hilo
        # distinto. El candado (_lock) serializa el acceso para que sea seguro.
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def remember(self, text: str) -> None:
        vector = np.asarray(self._embedder.embed(text), dtype=np.float32)
        with self._lock:
            self._conn.execute(
                "INSERT INTO memories (text, embedding, created_at) VALUES (?, ?, ?)",
                (text, vector.tobytes(), datetime.now().isoformat(timespec="seconds")),
            )
            self._conn.commit()

    def recall(self, query: str, k: int) -> list[MemoryItem]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, text, embedding, created_at FROM memories"
            ).fetchall()
        if not rows:
            return []

        query_vec = np.asarray(self._embedder.embed(query), dtype=np.float32)

        # Solo consideramos recuerdos cuyo vector tenga la MISMA dimensión que la
        # consulta. Así, si cambiaste de modelo de embeddings, los recuerdos
        # viejos (otra dimensión) se ignoran en vez de romper la búsqueda.
        rows = [r for r in rows if len(np.frombuffer(r[2], dtype=np.float32)) == query_vec.shape[0]]
        if not rows:
            return []

        matrix = np.stack([np.frombuffer(r[2], dtype=np.float32) for r in rows])
        scores = _cosine_similarities(query_vec, matrix)

        # Ordenamos por relevancia descendente y tomamos los k mejores.
        best = np.argsort(scores)[::-1][:k]
        return [
            MemoryItem(
                id=int(rows[i][0]),
                text=str(rows[i][1]),
                created_at=str(rows[i][3]),
                score=float(scores[i]),
            )
            for i in best
        ]

    def all(self) -> list[MemoryItem]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, text, created_at FROM memories ORDER BY id"
            ).fetchall()
        return [MemoryItem(id=int(r[0]), text=str(r[1]), created_at=str(r[2])) for r in rows]

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM memories")
            self._conn.commit()
