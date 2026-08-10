"""Plugin de ejemplo: tirar un dado.

Este es un plugin completo en un solo archivo. Para probarlo, copialo a tu
carpeta de plugins (~/.polo/plugins/) y reiniciá POLO. Vas a ver que POLO
aprende a tirar dados SIN que se haya tocado ni una línea del código de POLO.

Anatomía de un plugin:
1. Una o más clases de herramientas (cumplen el contrato Tool).
2. Una clase de plugin con name, version y tools().
3. Una variable a nivel de módulo llamada PLUGIN.
"""

from __future__ import annotations

import random
from typing import Any

from polo.core.ports.tool import RiskLevel


class DadoTool:
    """Tira un dado con la cantidad de caras que se pida."""

    name = "tirar_dado"
    description = (
        "Tira un dado y devuelve el resultado al azar. "
        "Argumento opcional: 'caras' (número de caras, por defecto 6)."
    )
    risk = RiskLevel.SAFE

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "caras": {
                    "type": "integer",
                    "description": "Número de caras del dado (por defecto 6).",
                }
            },
        }

    def run(self, arguments: dict[str, Any]) -> str:
        try:
            caras = int(arguments.get("caras", 6))
        except (TypeError, ValueError):
            caras = 6
        if caras < 2:
            return "Un dado necesita al menos 2 caras."
        resultado = random.randint(1, caras)
        return f"🎲 Salió un {resultado} (dado de {caras} caras)."


class DadoPlugin:
    """Plugin que le enseña a POLO a tirar dados."""

    name = "dado"
    version = "1.0.0"

    def tools(self) -> list[Any]:
        return [DadoTool()]


# POLO busca esta variable al cargar el archivo.
PLUGIN = DadoPlugin()
