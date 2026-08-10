"""Tests del embedder en la nube (NIM) y la guarda de dimensión de la memoria."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest

from polo.adapters.embedding.nim_embedding import NimEmbedder
from polo.core.errors import LLMUnavailableError


def _cliente_con_vector(vector: list[float]) -> MagicMock:
    cliente = MagicMock()
    cliente.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=vector)]
    )
    return cliente


def test_nim_embedder_devuelve_vector() -> None:
    embedder = NimEmbedder(
        model="nv-embed", api_key="x", client=_cliente_con_vector([0.1, 0.2, 0.3])
    )
    assert embedder.embed("hola") == [0.1, 0.2, 0.3]


def test_nim_embedder_error_da_mensaje_claro() -> None:
    cliente = MagicMock()
    cliente.embeddings.create.side_effect = RuntimeError("boom")
    embedder = NimEmbedder(model="nv-embed", api_key="x", client=cliente)

    with pytest.raises(LLMUnavailableError):
        embedder.embed("hola")


def test_memoria_ignora_vectores_de_otra_dimension(tmp_path: object) -> None:
    # Guardamos un recuerdo con un embedder de 3 dims, luego consultamos con uno
    # de 4 dims (como si hubiéramos cambiado de modelo). No debe romperse.
    from pathlib import Path

    from polo.adapters.memory.sqlite_memory import SqliteMemory

    class Embedder3:
        def embed(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0]

    class Embedder4:
        def embed(self, text: str) -> list[float]:
            return [1.0, 0.0, 0.0, 0.0]

    db = Path(str(tmp_path)) / "mem.db"
    mem3 = SqliteMemory(embedder=Embedder3(), db_path=db)
    mem3.remember("un recuerdo viejo")

    # Nueva sesión con embedder de otra dimensión, misma base.
    mem4 = SqliteMemory(embedder=Embedder4(), db_path=db)
    resultados = mem4.recall("algo", k=5)

    # El recuerdo viejo (3 dims) se ignora en vez de crashear.
    assert resultados == []


def test_cosine_sigue_andando_misma_dimension() -> None:
    q = np.array([1.0, 0.0], dtype=np.float32)
    m = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    from polo.adapters.memory.sqlite_memory import _cosine_similarities

    scores = _cosine_similarities(q, m)
    assert scores[0] > scores[1]  # el primero es idéntico a la consulta
