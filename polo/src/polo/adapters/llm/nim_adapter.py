"""Adaptador de cerebro en la nube: NVIDIA NIM (compatible con OpenAI).

Implementa el MISMO puerto LLMPort que Ollama, así que se intercambian con una
línea de config. Al ser compatible con OpenAI, este mismo adaptador sirve para
NIM y, a futuro, para cualquier proveedor con endpoint OpenAI.

La parte delicada: NIM (como OpenAI) exige que cada resultado de herramienta
apunte al 'id' de la llamada que lo pidió. POLO relaciona por nombre, así que acá
generamos esos ids y los enlazamos al traducir.
"""

from __future__ import annotations

import json
from typing import Any

import openai

from polo.core.errors import LLMUnavailableError
from polo.core.models import LLMResponse, Message, Role, ToolCall, ToolSpec
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.nim")


class NimAdapter:
    """Implementa LLMPort contra un endpoint compatible con OpenAI (NIM)."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        client: Any = None,
    ) -> None:
        self._model = model
        # El cliente es inyectable para testear sin llamar a la nube.
        self._client = client or openai.OpenAI(api_key=api_key, base_url=base_url)

    def generate(self, messages: list[Message], tools: list[ToolSpec] | None = None) -> LLMResponse:
        payload = self._messages_to_openai(messages)
        kwargs: dict[str, Any] = {"model": self._model, "messages": payload}
        if tools:
            kwargs["tools"] = [self._spec_to_openai(t) for t in tools]

        try:
            respuesta = self._client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as exc:
            log.error("nim_auth_error", error=str(exc))
            raise LLMUnavailableError(
                "Tu API key de NVIDIA (NIM) parece inválida. Revisá POLO_NIM_API_KEY en el .env."
            ) from exc
        except openai.APIError as exc:
            log.error("nim_api_error", error=str(exc))
            raise LLMUnavailableError(
                "No pude usar NVIDIA NIM (conexión, límite o modelo). "
                "POLO intentará con el cerebro local."
            ) from exc

        return self._message_from_openai(respuesta.choices[0].message)

    def health_check(self) -> None:
        """Verifica que la API key y el modelo funcionen (gasta 1 llamada)."""
        try:
            self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "hola"}],
                max_tokens=1,
            )
        except openai.AuthenticationError as exc:
            raise LLMUnavailableError(
                "Tu API key de NVIDIA (NIM) parece inválida. Revisá POLO_NIM_API_KEY en el .env."
            ) from exc
        except Exception as exc:  # noqa: BLE001 - cualquier fallo = NIM no usable
            raise LLMUnavailableError(
                f"No pude conectar con NVIDIA NIM (modelo '{self._model}'). "
                "Revisá tu conexión y el modelo configurado."
            ) from exc

    # ── Traducción POLO -> OpenAI ─────────────────────────────────────────

    def _messages_to_openai(self, messages: list[Message]) -> list[dict[str, Any]]:
        salida: list[dict[str, Any]] = []
        # Cola de (nombre, id) de las últimas tool_calls, para enlazar resultados.
        pendientes: list[tuple[str, str]] = []

        for i, m in enumerate(messages):
            if m.role is Role.TOOL:
                tcid = self._emparejar_id(pendientes, m.tool_name)
                salida.append({"role": "tool", "tool_call_id": tcid, "content": m.content})
            elif m.role is Role.ASSISTANT and m.tool_calls:
                pendientes = []
                llamadas = []
                for j, c in enumerate(m.tool_calls):
                    cid = f"call_{i}_{j}"
                    pendientes.append((c.name, cid))
                    llamadas.append(
                        {
                            "id": cid,
                            "type": "function",
                            "function": {
                                "name": c.name,
                                "arguments": json.dumps(c.arguments),
                            },
                        }
                    )
                salida.append(
                    {
                        "role": "assistant",
                        "content": m.content or None,
                        "tool_calls": llamadas,
                    }
                )
            else:
                salida.append({"role": m.role.value, "content": m.content})
        return salida

    @staticmethod
    def _emparejar_id(pendientes: list[tuple[str, str]], nombre: str | None) -> str:
        """Encuentra el id de la llamada que corresponde a este resultado."""
        for idx, (n, cid) in enumerate(pendientes):
            if n == nombre:
                pendientes.pop(idx)
                return cid
        if pendientes:
            return pendientes.pop(0)[1]
        return "call_0"  # fallback defensivo

    def _spec_to_openai(self, spec: ToolSpec) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }

    # ── Traducción OpenAI -> POLO ─────────────────────────────────────────

    def _message_from_openai(self, message: Any) -> LLMResponse:
        tool_calls: list[ToolCall] = []
        for tc in getattr(message, "tool_calls", None) or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(name=tc.function.name, arguments=args))
        return LLMResponse(text=message.content or "", tool_calls=tool_calls)
