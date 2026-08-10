"""Tests de los modelos del núcleo y verificación de contratos (puertos)."""

from __future__ import annotations

from polo.core.models import AssistantOutput, Message, Role, UserInput
from polo.core.ports.llm import LLMPort


def test_message_se_construye() -> None:
    msg = Message(role=Role.USER, content="hola")
    assert msg.role is Role.USER
    assert msg.content == "hola"


def test_user_input_metadata_por_defecto_vacio() -> None:
    entrada = UserInput(text="probando")
    assert entrada.text == "probando"
    assert entrada.metadata == {}


def test_una_implementacion_falsa_cumple_el_puerto_llm() -> None:
    """Un LLM de mentira debe 'contar' como LLMPort sin heredar de él.

    Esto valida que el contrato (Protocol) está bien definido: cualquier clase
    con la firma correcta encaja. Es la base de que los adaptadores sean
    intercambiables.
    """

    class LLMFalso:
        def generate(self, messages: list[Message]) -> AssistantOutput:
            return AssistantOutput(text="respuesta de mentira")

    falso = LLMFalso()
    # runtime_checkable permite verificar el Protocol en tiempo de ejecución.
    assert isinstance(falso, LLMPort)
    assert falso.generate([]).text == "respuesta de mentira"
