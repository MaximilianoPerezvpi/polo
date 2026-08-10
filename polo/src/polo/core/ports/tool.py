"""Puerto Tool: el contrato de una capacidad que POLO puede ejecutar.

Cada herramienta declara su nombre, qué hace, qué argumentos acepta, su nivel
de riesgo, y cómo se ejecuta. El modelo nunca ejecuta nada: solo *pide* usar
una herramienta por su nombre, y nuestro código (el registro) decide y ejecuta.
Esa separación es la base de la seguridad.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class RiskLevel(StrEnum):
    """Cuánto cuidado requiere ejecutar una herramienta."""

    SAFE = "safe"  # solo lectura, sin efectos secundarios: se ejecuta directo
    CONFIRM = "confirm"  # modifica algo: requiere confirmación del usuario


@runtime_checkable
class Tool(Protocol):
    """Una capacidad ejecutable de POLO."""

    @property
    def name(self) -> str:
        """Nombre único, corto, sin espacios (lo usa el modelo para llamarla)."""
        ...

    @property
    def description(self) -> str:
        """Qué hace, en lenguaje claro (el modelo lo lee para decidir usarla)."""
        ...

    @property
    def risk(self) -> RiskLevel:
        """Nivel de riesgo de ejecutarla."""
        ...

    def parameters(self) -> dict[str, Any]:
        """JSON Schema de los argumentos que acepta (vacío si no lleva)."""
        ...

    def run(self, arguments: dict[str, Any]) -> str:
        """Ejecuta la herramienta y devuelve el resultado como texto."""
        ...
