"""Puerto Confirmer: pedir una confirmación sí/no al usuario.

El núcleo necesita, a veces, preguntar "¿te parece bien que haga esto?" antes de
ejecutar una herramienta riesgosa. Pero el núcleo NO conoce la interfaz (podría
ser terminal, celular, máscara...). Así que pregunta a través de este puerto, y
cada interfaz decide cómo mostrar la pregunta.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ConfirmerPort(Protocol):
    """Pide una confirmación al usuario y devuelve si aceptó."""

    def confirm(self, prompt: str) -> bool:
        """Muestra `prompt` y devuelve True si el usuario acepta."""
        ...
