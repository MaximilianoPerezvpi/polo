"""Puerto de memoria de largo plazo.

El contrato de cómo POLO guarda y recupera lo que sabe sobre vos, entre
sesiones. En la Fase 2 lo implementamos con SQLite + búsqueda por similitud,
pero el núcleo solo conoce este contrato. Si algún día la memoria creciera
tanto que necesitáramos una base vectorial de verdad, se cambia el adaptador
y el núcleo no se toca.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from polo.core.models import MemoryItem


@runtime_checkable
class MemoryPort(Protocol):
    """Almacén de recuerdos de largo plazo."""

    def remember(self, text: str) -> None:
        """Guarda un nuevo recuerdo."""
        ...

    def recall(self, query: str, k: int) -> list[MemoryItem]:
        """Devuelve los k recuerdos más relevantes para la consulta."""
        ...

    def all(self) -> list[MemoryItem]:
        """Devuelve todos los recuerdos (para inspección)."""
        ...

    def clear(self) -> None:
        """Borra toda la memoria."""
        ...
