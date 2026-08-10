"""Herramienta para escribir archivos de texto.

Primera herramienta que MODIFICA el mundo, así que estrena el mecanismo de
seguridad. Dos capas de protección:

1. RiskLevel.CONFIRM: el usuario debe autorizar antes de que se ejecute.
2. Sandbox: los archivos SOLO se pueden escribir dentro de la carpeta de trabajo
   de POLO. Aunque el modelo (o el usuario) pida escribir en C:\\Windows o en
   cualquier lado, el nombre se sanea y el archivo cae en el workspace. El modelo
   no puede escapar de esa carpeta.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polo.core.ports.tool import RiskLevel


class WriteFileTool:
    """Escribe un archivo de texto, solo dentro del workspace de POLO."""

    name = "escribir_archivo"
    description = (
        "Crea o sobrescribe un archivo de texto en la carpeta de trabajo de POLO. "
        "Argumentos: 'nombre' (nombre del archivo) y 'contenido' (el texto)."
    )
    risk = RiskLevel.CONFIRM

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nombre": {
                    "type": "string",
                    "description": "Nombre del archivo (sin carpetas).",
                },
                "contenido": {
                    "type": "string",
                    "description": "El texto a escribir.",
                },
            },
            "required": ["nombre", "contenido"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        nombre = str(arguments.get("nombre", "")).strip()
        contenido = str(arguments.get("contenido", ""))
        if not nombre:
            return "Error: no se indicó un nombre de archivo."

        # Sandbox: nos quedamos SOLO con el nombre, descartando cualquier carpeta
        # o intento de salir (../, rutas absolutas, etc.).
        seguro = Path(nombre).name
        if not seguro or seguro in {".", ".."}:
            return "Error: nombre de archivo inválido."

        self._workspace.mkdir(parents=True, exist_ok=True)
        destino = self._workspace / seguro
        try:
            destino.write_text(contenido, encoding="utf-8")
        except OSError as exc:
            return f"No pude escribir el archivo: {exc}"
        return f"Archivo guardado en {destino}"
