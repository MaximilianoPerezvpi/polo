"""Tests del adaptador de Ollama sin un servidor real.

Mockeamos el cliente de Ollama para verificar dos cosas:
1. Que traduce bien nuestros Message al formato que Ollama espera.
2. Que convierte un fallo de conexión en un error de dominio limpio.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from polo.adapters.llm.ollama_adapter import OllamaAdapter
from polo.core.errors import LLMUnavailableError
from polo.core.models import Message, Role


def _adapter_con_cliente_falso(cliente: Any) -> OllamaAdapter:
    adapter = OllamaAdapter(model="modelo-de-prueba")
    adapter._client = cliente  # inyectamos el cliente falso
    return adapter


def test_traduce_mensajes_al_formato_ollama() -> None:
    # Cliente falso que captura lo que recibe y devuelve una respuesta armada.
    respuesta = MagicMock()
    respuesta.message.content = "hola desde el modelo"
    cliente = MagicMock()
    cliente.chat.return_value = respuesta

    adapter = _adapter_con_cliente_falso(cliente)
    salida = adapter.generate([Message(role=Role.USER, content="hola")])

    # Verificamos la traducción de vuelta.
    assert salida.text == "hola desde el modelo"

    # Verificamos la traducción de ida: role como string, content correcto.
    _, kwargs = cliente.chat.call_args
    enviado = kwargs["messages"]
    assert enviado == [{"role": "user", "content": "hola"}]


def test_conexion_fallida_se_convierte_en_error_de_dominio() -> None:
    cliente = MagicMock()
    cliente.chat.side_effect = ConnectionError("sin conexión")

    adapter = _adapter_con_cliente_falso(cliente)

    # No debe filtrar el error crudo; debe ser nuestro error de dominio.
    with pytest.raises(LLMUnavailableError):
        adapter.generate([Message(role=Role.USER, content="hola")])
