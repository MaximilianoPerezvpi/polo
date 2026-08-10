"""Puerto Interface: el contrato de cualquier medio por el que POLO habla.

Este es EL puerto que hace realidad tu visión: la PC, el celular, la máscara y
los lentes serán todos implementaciones de este mismo contrato. El núcleo
recibe un `UserInput` con `receive()` y entrega un `AssistantOutput` con
`present()`. No sabe si detrás hay una terminal o una máscara de Spider-Man.

Agregar una interfaz nueva en el futuro = escribir UNA clase que cumpla esto.
Cero cambios en el núcleo.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from polo.core.models import AssistantOutput, UserInput


@runtime_checkable
class InterfacePort(Protocol):
    """Un canal de entrada/salida entre el usuario y POLO."""

    def receive(self) -> UserInput:
        """Obtiene la siguiente entrada del usuario (texto, voz transcrita...)."""
        ...

    def present(self, output: AssistantOutput) -> None:
        """Muestra/reproduce la respuesta de POLO por este medio."""
        ...
