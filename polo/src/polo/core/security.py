"""Política de seguridad: archivos y carpetas que POLO NUNCA debe tocar.

Inspirado en la lista de OpenJarvis. La idea: aunque el usuario (o el modelo)
pida leer/mover/abrir algo, si toca claves, credenciales o secretos, POLO se
niega. Es una red de seguridad para que un pedido descuidado no exponga datos
sensibles.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

# Patrones de nombre de archivo (con comodín) que se bloquean.
_GLOBS_BLOQUEADOS = ("*.pem", "*.key", "*.p12", "*.pfx", "*.ppk")

# Segmentos de ruta (carpeta o archivo con nombre exacto) que se bloquean.
_SEGMENTOS_BLOQUEADOS = frozenset(
    {
        ".ssh",
        ".gnupg",
        ".aws",
        ".env",
        "credentials",
        "id_rsa",
        "id_ed25519",
        "shadow",
        "passwd",
        "token",
        "secret",
        "secrets",
        ".netrc",
        "wallet.dat",
    }
)


def is_sensitive_path(path: Path) -> bool:
    """True si la ruta toca algo sensible que POLO no debe leer/mover/abrir."""
    p = path.expanduser()
    nombre = p.name.lower()

    # 1) El nombre del archivo coincide con un patrón sensible (*.pem, *.key...).
    if any(fnmatch.fnmatch(nombre, glob) for glob in _GLOBS_BLOQUEADOS):
        return True

    # 2) Algún segmento de la ruta es exactamente un nombre sensible.
    segmentos = {parte.lower() for parte in p.parts}
    return bool(segmentos & _SEGMENTOS_BLOQUEADOS)


# Mensaje único para cuando se rechaza el acceso.
BLOQUEADO_MSG = (
    "Por seguridad, no accedo a archivos o carpetas sensibles (claves, credenciales, secretos)."
)
