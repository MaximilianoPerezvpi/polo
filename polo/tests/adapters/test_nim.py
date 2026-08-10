"""Tests del cerebro en la nube (NIM) y del respaldo, sin llamar a la nube."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from polo.adapters.llm.fallback import FallbackLLM
from polo.adapters.llm.nim_adapter import NimAdapter
from polo.core.errors import LLMUnavailableError
from polo.core.models import LLMResponse, Message, Role, ToolCall, ToolSpec


def _respuesta_openai(content: str, tool_calls: list[Any] | None = None) -> Any:
    mensaje = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


def _nim_con_cliente() -> tuple[NimAdapter, MagicMock]:
    cliente = MagicMock()
    adapter = NimAdapter(model="meta/llama-3.1-70b-instruct", api_key="x", client=cliente)
    return adapter, cliente


def test_nim_texto_simple() -> None:
    adapter, cliente = _nim_con_cliente()
    cliente.chat.completions.create.return_value = _respuesta_openai("Hola Maxi")

    resp = adapter.generate([Message(role=Role.USER, content="hola")])

    assert isinstance(resp, LLMResponse)
    assert resp.text == "Hola Maxi"
    assert resp.tool_calls == []


def test_nim_parsea_tool_calls() -> None:
    adapter, cliente = _nim_con_cliente()
    tc = SimpleNamespace(function=SimpleNamespace(name="volumen", arguments='{"accion": "subir"}'))
    cliente.chat.completions.create.return_value = _respuesta_openai("", [tc])

    resp = adapter.generate([Message(role=Role.USER, content="subí")])

    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "volumen"
    assert resp.tool_calls[0].arguments == {"accion": "subir"}


def test_nim_traduce_herramientas_al_formato_openai() -> None:
    adapter, cliente = _nim_con_cliente()
    cliente.chat.completions.create.return_value = _respuesta_openai("ok")

    spec = ToolSpec(name="reloj", description="Da la hora", parameters={"type": "object"})
    adapter.generate([Message(role=Role.USER, content="hora")], tools=[spec])

    _, kwargs = cliente.chat.completions.create.call_args
    herramienta = kwargs["tools"][0]
    assert herramienta["type"] == "function"
    assert herramienta["function"]["name"] == "reloj"


def test_nim_enlaza_resultado_de_herramienta_con_su_id() -> None:
    # Un historial con una tool_call del asistente y su resultado: el resultado
    # debe llevar el tool_call_id del que lo pidió (lo que exige NIM/OpenAI).
    adapter, cliente = _nim_con_cliente()
    cliente.chat.completions.create.return_value = _respuesta_openai("listo")

    historial = [
        Message(role=Role.USER, content="subí"),
        Message(
            role=Role.ASSISTANT,
            tool_calls=[ToolCall(name="volumen", arguments={"accion": "subir"})],
        ),
        Message(role=Role.TOOL, content="Subí el volumen.", tool_name="volumen"),
    ]
    adapter.generate(historial)

    _, kwargs = cliente.chat.completions.create.call_args
    payload = kwargs["messages"]
    asistente = next(m for m in payload if m["role"] == "assistant")
    resultado = next(m for m in payload if m["role"] == "tool")
    # El id que generó el asistente debe coincidir con el del resultado.
    assert asistente["tool_calls"][0]["id"] == resultado["tool_call_id"]
    # Y los argumentos van como string JSON.
    assert json.loads(asistente["tool_calls"][0]["function"]["arguments"]) == {"accion": "subir"}


def test_nim_key_invalida_da_error_claro() -> None:
    import openai

    adapter, cliente = _nim_con_cliente()
    cliente.chat.completions.create.side_effect = openai.AuthenticationError(
        message="bad key", response=MagicMock(status_code=401), body=None
    )

    with pytest.raises(LLMUnavailableError) as exc:
        adapter.generate([Message(role=Role.USER, content="hola")])
    assert "key" in str(exc.value).lower()


# ── Respaldo ────────────────────────────────────────────────────────────────


class LLMFalso:
    def __init__(self, texto: str) -> None:
        self._texto = texto
        self.llamado = False

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        self.llamado = True
        return LLMResponse(text=self._texto)


class LLMRoto:
    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        raise LLMUnavailableError("nube caída")


def test_fallback_usa_primario_si_anda() -> None:
    primario = LLMFalso("desde la nube")
    respaldo = LLMFalso("desde local")

    resp = FallbackLLM(primario, respaldo).generate([Message(role=Role.USER)])

    assert resp.text == "desde la nube"
    assert not respaldo.llamado  # no se tocó el respaldo


def test_fallback_cae_a_local_si_primario_falla() -> None:
    respaldo = LLMFalso("desde local")

    resp = FallbackLLM(LLMRoto(), respaldo).generate([Message(role=Role.USER)])

    assert resp.text == "desde local"
    assert respaldo.llamado
