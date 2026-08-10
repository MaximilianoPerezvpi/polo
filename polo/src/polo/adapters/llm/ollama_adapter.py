"""Adaptador de Ollama: implementa LLMPort usando un modelo local.

Único archivo de POLO que conoce Ollama. Traduce entre el mundo de POLO y el de
Ollama, en ambos sentidos, incluyendo las herramientas (Fase 3).
"""

from __future__ import annotations

from typing import Any

import ollama
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from polo.core.errors import LLMUnavailableError
from polo.core.models import LLMResponse, Message, ToolCall, ToolSpec
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.ollama")


class OllamaAdapter:
    """Implementación de LLMPort respaldada por un modelo local de Ollama."""

    def __init__(
        self,
        model: str,
        host: str = "http://localhost:11434",
        keep_alive: str = "30m",
    ) -> None:
        self._model = model
        self._client = ollama.Client(host=host)
        self._keep_alive = keep_alive

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        payload = [self._message_to_ollama(m) for m in messages]
        ollama_tools = [self._spec_to_ollama(t) for t in tools] if tools else None

        try:
            message = self._chat(payload, ollama_tools)
        except ollama.ResponseError as exc:
            log.error("ollama_response_error", error=str(exc))
            raise LLMUnavailableError(
                f"El modelo '{self._model}' falló. ¿Lo descargaste con 'ollama pull'?"
            ) from exc
        except (ConnectionError, ollama.RequestError) as exc:
            log.error("ollama_connection_error", error=str(exc))
            raise LLMUnavailableError(
                "No pude conectar con Ollama. ¿Está corriendo la aplicación?"
            ) from exc

        return self._message_from_ollama(message)

    # ── Traducción POLO -> Ollama ─────────────────────────────────────────

    def _message_to_ollama(self, m: Message) -> dict[str, Any]:
        out: dict[str, Any] = {"role": m.role.value, "content": m.content}
        if m.tool_calls:
            out["tool_calls"] = [
                {"function": {"name": c.name, "arguments": c.arguments}} for c in m.tool_calls
            ]
        if m.tool_name is not None:
            out["tool_name"] = m.tool_name
        return out

    def _spec_to_ollama(self, spec: ToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }

    # ── Traducción Ollama -> POLO ─────────────────────────────────────────

    def _message_from_ollama(self, message: ollama.Message) -> LLMResponse:
        tool_calls: list[ToolCall] = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        name=tc.function.name,
                        arguments=dict(tc.function.arguments),
                    )
                )
        return LLMResponse(text=message.content or "", tool_calls=tool_calls)

    def health_check(
        self, extra_models: list[str] | None = None, *, include_self: bool = True
    ) -> None:
        """Verifica que Ollama esté corriendo y los modelos disponibles.

        Lanza LLMUnavailableError con un mensaje claro y accionable si Ollama no
        responde o si falta algún modelo requerido. Con include_self=False no
        exige el modelo de chat propio (útil si el chat lo hace otro cerebro y
        Ollama solo aporta embeddings).
        """
        try:
            respuesta = self._client.list()
        except Exception as exc:  # noqa: BLE001 - cualquier fallo = Ollama no disponible
            raise LLMUnavailableError(
                "No puedo conectar con Ollama. ¿Está corriendo? "
                "Abrí la app de Ollama (o ejecutá 'ollama serve') y reintentá."
            ) from exc

        # Nombres de modelos disponibles (robusto ante distintas versiones).
        disponibles: set[str] = set()
        for m in getattr(respuesta, "models", []) or []:
            nombre = getattr(m, "model", None) or getattr(m, "name", None)
            if isinstance(m, dict):
                nombre = m.get("model") or m.get("name")
            if nombre:
                disponibles.add(str(nombre))

        requeridos = ([self._model] if include_self else []) + (extra_models or [])
        faltan = [req for req in requeridos if not any(req in disp for disp in disponibles)]
        if faltan:
            comandos = " ; ".join(f"ollama pull {m}" for m in faltan)
            raise LLMUnavailableError(
                f"Faltan modelos de Ollama: {', '.join(faltan)}. Descargalos con: {comandos}"
            )

    @retry(
        retry=retry_if_exception_type(ConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True,
    )
    def _chat(
        self, payload: list[dict[str, Any]], tools: list[dict[str, Any]] | None
    ) -> ollama.Message:
        response = self._client.chat(
            model=self._model,
            messages=payload,
            tools=tools,
            keep_alive=self._keep_alive,
        )
        return response.message
