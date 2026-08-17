"""Control de PC: volumen del sistema y abrir aplicaciones.

Específicas de Windows. Diseñadas con backends inyectables para poder testear
la lógica sin tocar el audio ni lanzar programas de verdad.

Seguridad:
- El volumen es SAFE (reversible, inofensivo).
- Abrir una aplicación es CONFIRM (lanza un programa: el usuario autoriza).
- 'abrir_aplicacion' rechaza nombres con caracteres peligrosos (defensa extra),
  y NO usa una shell (evita inyección de comandos).
"""

from __future__ import annotations

import ctypes
import os
import subprocess
from collections.abc import Callable
from typing import Any

from polo.core.ports.tool import RiskLevel
from polo.logging_setup import get_logger

log = get_logger("polo.adapters.pc_control")

# Códigos de tecla multimedia de Windows para el volumen.
_VK_VOLUMEN = {
    "subir": 0xAF,  # VK_VOLUME_UP
    "bajar": 0xAE,  # VK_VOLUME_DOWN
    "silenciar": 0xAD,  # VK_VOLUME_MUTE
}

# Códigos de tecla multimedia para controlar la reproducción de música.
# Funcionan con cualquier reproductor (Spotify, YouTube...), sin API ni Premium.
_VK_MUSICA = {
    "pausar": 0xB3,  # VK_MEDIA_PLAY_PAUSE (pausa o reanuda)
    "reanudar": 0xB3,  # mismo: alterna play/pausa
    "siguiente": 0xB0,  # VK_MEDIA_NEXT_TRACK
    "anterior": 0xB1,  # VK_MEDIA_PREV_TRACK
}
_KEYEVENTF_KEYUP = 2

# Un "presser" presiona una tecla multimedia por su código.
Presser = Callable[[int], None]
# Un "launcher" abre una aplicación por su nombre.
Launcher = Callable[[str], None]

# Caracteres que no permitimos en un nombre de aplicación (defensa extra).
_PELIGROSOS = set("&|;<>%\"'`\n\r")


def _presionar_real(vk: int) -> None:
    """Presiona (y suelta) una tecla multimedia vía la API de Windows."""
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        raise RuntimeError("El control de volumen solo funciona en Windows.")
    windll.user32.keybd_event(vk, 0, 0, 0)  # tecla abajo
    windll.user32.keybd_event(vk, 0, _KEYEVENTF_KEYUP, 0)  # tecla arriba


def _lanzar_real(nombre: str) -> None:
    """Abre una aplicación por su nombre (sin shell, para evitar inyección)."""
    startfile = getattr(os, "startfile", None)
    if startfile is not None:
        startfile(nombre)  # Windows: resuelve apps registradas, protocolos, etc.
    else:
        subprocess.run(["xdg-open", nombre], check=False)  # fallback no-Windows


class VolumeTool:
    """Sube, baja o silencia el volumen del sistema."""

    final = True
    name = "volumen"
    description = (
        "Controla el volumen del sistema. Argumento 'accion': 'subir', 'bajar' "
        "o 'silenciar'. Argumento opcional 'cantidad' (cuántos pasos, por "
        "defecto 5)."
    )
    risk = RiskLevel.SAFE

    def __init__(self, presser: Presser | None = None) -> None:
        self._presser = presser or _presionar_real

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "accion": {
                    "type": "string",
                    "enum": ["subir", "bajar", "silenciar"],
                    "description": "Qué hacer con el volumen.",
                },
                "cantidad": {
                    "type": "integer",
                    "description": "Cuántos pasos subir o bajar (por defecto 5).",
                },
            },
            "required": ["accion"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        accion = str(arguments.get("accion", "")).lower().strip()
        vk = _VK_VOLUMEN.get(accion)
        if vk is None:
            return "Acción inválida. Usá: subir, bajar o silenciar."

        try:
            if accion == "silenciar":
                self._presser(vk)
                return "Silencié (o reactivé) el volumen."

            try:
                cantidad = int(arguments.get("cantidad", 5))
            except (TypeError, ValueError):
                cantidad = 5
            cantidad = max(1, min(cantidad, 50))
            for _ in range(cantidad):
                self._presser(vk)
        except Exception as exc:  # noqa: BLE001 - el control de audio puede fallar
            return f"No pude cambiar el volumen: {exc}"

        return f"{'Subí' if accion == 'subir' else 'Bajé'} el volumen."


class OpenAppTool:
    """Abre una aplicación por su nombre."""

    final = True
    name = "abrir_aplicacion"
    description = (
        "Abre una aplicación por su nombre (ej: chrome, notepad, spotify). Argumento: 'nombre'."
    )
    risk = RiskLevel.CONFIRM

    def __init__(self, launcher: Launcher | None = None) -> None:
        self._launcher = launcher or _lanzar_real

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "nombre": {
                    "type": "string",
                    "description": "Nombre de la aplicación a abrir.",
                }
            },
            "required": ["nombre"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        nombre = str(arguments.get("nombre", "")).strip()
        if not nombre:
            return "Error: no se indicó qué aplicación abrir."
        if any(c in _PELIGROSOS for c in nombre):
            return "Nombre de aplicación inválido."

        try:
            self._launcher(nombre)
        except Exception as exc:  # noqa: BLE001 - la app puede no existir
            return f"No pude abrir '{nombre}': {exc}"

        log.info("pc_abrir_aplicacion", nombre=nombre)
        return f"Abrí {nombre}."


class MediaControlTool:
    """Controla la reproducción de música (Spotify, YouTube, cualquier player)."""

    final = True
    name = "control_musica"
    description = (
        "Controla la música que esté sonando en cualquier reproductor (Spotify, "
        "YouTube, etc.). Argumento 'accion': 'pausar' (pausa o reanuda), "
        "'siguiente' o 'anterior'."
    )
    risk = RiskLevel.SAFE

    def __init__(self, presser: Presser | None = None) -> None:
        self._presser = presser or _presionar_real

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "accion": {
                    "type": "string",
                    "enum": ["pausar", "reanudar", "siguiente", "anterior"],
                    "description": "Qué hacer con la reproducción.",
                }
            },
            "required": ["accion"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        accion = str(arguments.get("accion", "")).lower().strip()
        vk = _VK_MUSICA.get(accion)
        if vk is None:
            return "Acción inválida. Usá: pausar, reanudar, siguiente o anterior."
        try:
            self._presser(vk)
        except Exception as exc:  # noqa: BLE001 - el control multimedia puede fallar
            return f"No pude controlar la música: {exc}"

        mensajes = {
            "pausar": "Pausé o reanudé la música.",
            "reanudar": "Pausé o reanudé la música.",
            "siguiente": "Pasé a la siguiente canción.",
            "anterior": "Volví a la canción anterior.",
        }
        return mensajes[accion]
