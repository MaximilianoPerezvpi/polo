"""Registro de herramientas: el guardián entre el modelo y las capacidades.

El modelo pide usar una herramienta por su nombre. El registro:
1. La busca en su catálogo.
2. Si es riesgosa, pide confirmación al usuario (vía ConfirmerPort).
3. La ejecuta de forma controlada y devuelve el resultado.

Si algo falla, devuelve el error como texto (no rompe la conversación): el
modelo puede leer ese error y reaccionar. El núcleo nunca deja que una
herramienta lo tumbe.
"""

from __future__ import annotations

from polo.core.models import ToolCall, ToolSpec
from polo.core.ports.confirm import ConfirmerPort
from polo.core.ports.tool import RiskLevel, Tool


class ToolRegistry:
    """Cataloga y ejecuta herramientas con control de permisos."""

    def __init__(self, tools: list[Tool], confirmer: ConfirmerPort | None = None) -> None:
        self._tools: dict[str, Tool] = {t.name: t for t in tools}
        self._confirmer = confirmer

    def specs(self) -> list[ToolSpec]:
        """Las descripciones de todas las herramientas, para ofrecérselas al modelo."""
        return [
            ToolSpec(name=t.name, description=t.description, parameters=t.parameters())
            for t in self._tools.values()
        ]

    def execute(self, call: ToolCall) -> str:
        """Ejecuta una herramienta pedida por el modelo, con control de permisos."""
        tool = self._tools.get(call.name)
        if tool is None:
            return f"Error: no existe una herramienta llamada '{call.name}'."

        # Puerta de seguridad: las herramientas riesgosas requieren confirmación.
        if tool.risk is RiskLevel.CONFIRM:
            pregunta = f"¿Permitís que POLO use la herramienta '{tool.name}'?"
            if self._confirmer is None or not self._confirmer.confirm(pregunta):
                return "El usuario no autorizó ejecutar esta herramienta."

        # Ejecución controlada: un fallo de la herramienta no tumba a POLO.
        try:
            return tool.run(call.arguments)
        except Exception as exc:  # noqa: BLE001 - frontera de robustez a propósito
            return f"Error al ejecutar '{tool.name}': {exc}"

    def __len__(self) -> int:
        return len(self._tools)
