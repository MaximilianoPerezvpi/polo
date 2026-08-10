"""Herramientas de automatización: interactúan con el sistema operativo.

Esta es la fase más delicada. Principios de seguridad aplicados aquí:

- Lo de solo lectura (listar) es SAFE.
- Lo que modifica o lanza algo (abrir, mover) es CONFIRM: el usuario autoriza.
- 'abrir' bloquea ejecutables (.exe, .bat, ...) para no lanzar programas peligrosos.
- 'mover' se niega a sobrescribir un archivo existente.
- Cada acción con efecto se registra en el log (auditoría).
- NO existe una herramienta de "ejecutar comando arbitrario": eso sería control
  total del sistema, y queda deliberadamente afuera.

El 'opener' (cómo se abre algo) es inyectable para poder testear sin lanzar nada.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from polo.core.ports.tool import RiskLevel
from polo.core.security import BLOQUEADO_MSG, is_sensitive_path
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.automation")

# Extensiones que 'abrir' NO va a abrir, para no lanzar programas peligrosos.
_EJECUTABLES = {
    ".exe",
    ".bat",
    ".cmd",
    ".ps1",
    ".scr",
    ".msi",
    ".com",
    ".vbs",
    ".js",
}

# Un opener recibe (destino, es_url) y lo abre.
Opener = Callable[[str, bool], None]


def _abrir_real(destino: str, es_url: bool) -> None:
    """Abre de verdad: navegador para URLs, programa por defecto para archivos."""
    if es_url:
        webbrowser.open(destino)
        return
    # os.startfile solo existe en Windows; en otros SO usamos un fallback.
    startfile = getattr(os, "startfile", None)
    if startfile is not None:
        startfile(destino)
    else:
        subprocess.run(["xdg-open", destino], check=False)


def _es_url(texto: str) -> bool:
    return texto.startswith(("http://", "https://"))


class ListFolderTool:
    """Lista el contenido de una carpeta (solo lectura)."""

    name = "listar_carpeta"
    description = "Lista los archivos y carpetas dentro de una carpeta. Argumento: 'ruta'."
    risk = RiskLevel.SAFE

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"ruta": {"type": "string", "description": "Ruta de la carpeta."}},
            "required": ["ruta"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        ruta = str(arguments.get("ruta", "")).strip()
        if not ruta:
            return "Error: no se indicó la carpeta."
        path = Path(ruta).expanduser()
        if is_sensitive_path(path):
            return BLOQUEADO_MSG
        if not path.is_dir():
            return f"No existe una carpeta en '{ruta}'."

        entradas = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        if not entradas:
            return f"La carpeta {path} está vacía."

        lineas = [f"{'📁' if e.is_dir() else '📄'} {e.name}" for e in entradas[:100]]
        extra = "" if len(entradas) <= 100 else f"\n... y {len(entradas) - 100} más"
        return f"Contenido de {path}:\n" + "\n".join(lineas) + extra


class OpenItemTool:
    """Abre un archivo con su programa por defecto, o una URL en el navegador."""

    name = "abrir"
    description = (
        "Abre un archivo (con su programa por defecto) o una URL en el navegador. "
        "Argumento: 'destino' (ruta de un archivo o una URL)."
    )
    risk = RiskLevel.CONFIRM

    def __init__(self, opener: Opener | None = None) -> None:
        self._opener = opener or _abrir_real

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "destino": {
                    "type": "string",
                    "description": "Ruta de un archivo o una URL (http/https).",
                }
            },
            "required": ["destino"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        destino = str(arguments.get("destino", "")).strip()
        if not destino:
            return "Error: no se indicó qué abrir."

        if _es_url(destino):
            self._opener(destino, True)
            log.info("automation_abrir_url", url=destino)
            return f"Abrí {destino} en el navegador."

        path = Path(destino).expanduser()
        if is_sensitive_path(path):
            return BLOQUEADO_MSG
        if not path.exists():
            return f"No existe '{destino}'."
        if path.suffix.lower() in _EJECUTABLES:
            return "Por seguridad, no abro archivos ejecutables."

        self._opener(str(path), False)
        log.info("automation_abrir_archivo", archivo=str(path))
        return f"Abrí {path.name}."


class MoveFileTool:
    """Mueve o renombra un archivo, sin sobrescribir."""

    name = "mover_archivo"
    description = "Mueve o renombra un archivo. Argumentos: 'origen' y 'destino' (rutas)."
    risk = RiskLevel.CONFIRM

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "origen": {"type": "string", "description": "Ruta del archivo."},
                "destino": {"type": "string", "description": "Ruta nueva."},
            },
            "required": ["origen", "destino"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        origen = Path(str(arguments.get("origen", "")).strip()).expanduser()
        destino = Path(str(arguments.get("destino", "")).strip()).expanduser()

        if is_sensitive_path(origen) or is_sensitive_path(destino):
            return BLOQUEADO_MSG
        if not origen.is_file():
            return f"No existe el archivo origen '{origen}'."
        if destino.exists():
            return "Ya existe algo en el destino; no lo sobrescribo por seguridad."
        if not destino.parent.is_dir():
            return f"La carpeta destino '{destino.parent}' no existe."

        try:
            shutil.move(str(origen), str(destino))
        except OSError as exc:
            return f"No pude mover el archivo: {exc}"

        log.info("automation_mover", origen=str(origen), destino=str(destino))
        return f"Moví {origen.name} a {destino}."
