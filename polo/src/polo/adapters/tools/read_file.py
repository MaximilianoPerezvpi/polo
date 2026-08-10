"""Herramienta para leer archivos de texto.

Solo lectura, así que es SAFE. Aun así, tiene guardas sensatas: límite de tamaño
(para no inundar el contexto del modelo) y lectura como texto tolerante a errores
de codificación.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polo.core.ports.tool import RiskLevel
from polo.core.security import BLOQUEADO_MSG, is_sensitive_path

_MAX_CHARS = 20_000


class ReadFileTool:
    """Lee el contenido de un archivo de texto que el usuario indique."""

    name = "leer_archivo"
    description = (
        "Lee y devuelve el contenido de un archivo de texto. "
        "Argumento: 'ruta' (la ruta completa del archivo)."
    )
    risk = RiskLevel.SAFE

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ruta": {
                    "type": "string",
                    "description": "Ruta completa del archivo a leer.",
                }
            },
            "required": ["ruta"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        ruta = str(arguments.get("ruta", "")).strip()
        if not ruta:
            return "Error: no se indicó ninguna ruta."

        path = Path(ruta).expanduser()
        if is_sensitive_path(path):
            return BLOQUEADO_MSG
        if not path.is_file():
            return f"No existe un archivo en '{ruta}'."

        try:
            contenido = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"No pude leer '{ruta}': {exc}"

        if len(contenido) > _MAX_CHARS:
            contenido = contenido[:_MAX_CHARS] + "\n... (contenido truncado)"
        return f"Contenido de {path.name}:\n{contenido}"
