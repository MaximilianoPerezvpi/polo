"""Tests del chequeo de salud (Ollama caído o modelos faltantes)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from polo.adapters.llm.ollama_adapter import OllamaAdapter
from polo.core.errors import LLMUnavailableError


def _adapter_con_modelos(nombres: list[str]) -> OllamaAdapter:
    adapter = OllamaAdapter(model="qwen2.5:3b")
    cliente = MagicMock()
    cliente.list.return_value = SimpleNamespace(models=[SimpleNamespace(model=n) for n in nombres])
    adapter._client = cliente
    return adapter


def test_ollama_caido_da_mensaje_claro() -> None:
    adapter = OllamaAdapter(model="qwen2.5:3b")
    cliente = MagicMock()
    cliente.list.side_effect = ConnectionError("boom")
    adapter._client = cliente

    with pytest.raises(LLMUnavailableError) as exc:
        adapter.health_check()

    assert "ollama" in str(exc.value).lower()
    assert "corriendo" in str(exc.value).lower()


def test_modelo_faltante_sugiere_pull() -> None:
    adapter = _adapter_con_modelos(["otra-cosa:1b"])

    with pytest.raises(LLMUnavailableError) as exc:
        adapter.health_check()

    assert "ollama pull qwen2.5:3b" in str(exc.value)


def test_todo_ok_no_lanza() -> None:
    adapter = _adapter_con_modelos(["qwen2.5:3b", "nomic-embed-text:latest"])
    # No debe lanzar nada.
    adapter.health_check(["nomic-embed-text"])


def test_detecta_falta_de_embeddings() -> None:
    adapter = _adapter_con_modelos(["qwen2.5:3b"])

    with pytest.raises(LLMUnavailableError) as exc:
        adapter.health_check(["nomic-embed-text"])

    assert "nomic-embed-text" in str(exc.value)
