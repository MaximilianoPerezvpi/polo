"""Modelos de datos del núcleo.

Objetos comunes que viajan entre el orquestador, las interfaces y los
adaptadores. Simples y sin dependencias de tecnologías externas.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Role(StrEnum):
    """Quién emite un mensaje dentro de una conversación."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"  # resultado de ejecutar una herramienta (Fase 3)


class ToolCall(BaseModel):
    """Una petición del modelo para usar una herramienta."""

    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """Un turno individual dentro de una conversación."""

    role: Role
    content: str = ""
    # Solo en turnos del asistente que piden herramientas (Fase 3).
    tool_calls: list[ToolCall] = Field(default_factory=list)
    # Solo en turnos con el resultado de una herramienta.
    tool_name: str | None = None


class UserInput(BaseModel):
    """Algo que el usuario le envía a POLO, sin importar por qué interfaz."""

    text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class AssistantOutput(BaseModel):
    """La respuesta final de POLO, lista para que una interfaz la presente."""

    text: str


class MemoryItem(BaseModel):
    """Un recuerdo de largo plazo: un hecho que POLO guarda entre sesiones."""

    text: str
    id: int | None = None
    created_at: str | None = None
    score: float | None = None


class ToolSpec(BaseModel):
    """La descripción de una herramienta que se le ofrece al modelo.

    `parameters` es un JSON Schema que describe los argumentos que acepta.
    """

    name: str
    description: str
    parameters: dict[str, Any]


class LLMResponse(BaseModel):
    """Lo que devuelve el modelo: texto, o una petición de usar herramientas.

    Si `tool_calls` está vacío, `text` es la respuesta final. Si no, el modelo
    quiere que ejecutemos esas herramientas y le devolvamos los resultados.
    """

    text: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
