"""Herramienta para abrir sitios web en el navegador.

Abre sitios conocidos por nombre (gmail, calendario, drive, instagram...), o una
URL/dominio cualquiera, o —si no reconoce— busca en Google. Da acceso liviano a
Gmail y Google Calendar sin necesidad de OAuth.

El "abridor" es inyectable para testear sin navegador.
"""

from __future__ import annotations

import urllib.parse
import webbrowser
from collections.abc import Callable
from typing import Any

from polo.core.ports.tool import RiskLevel

Opener = Callable[[str], Any]

# Sitios conocidos por nombre (en español y variantes comunes).
_SITIOS = {
    "gmail": "https://mail.google.com",
    "correo": "https://mail.google.com",
    "email": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "calendario": "https://calendar.google.com",
    "calendar": "https://calendar.google.com",
    "agenda": "https://calendar.google.com",
    "drive": "https://drive.google.com",
    "docs": "https://docs.google.com",
    "youtube": "https://www.youtube.com",
    "instagram": "https://www.instagram.com",
    "whatsapp": "https://web.whatsapp.com",
    "maps": "https://maps.google.com",
    "mapas": "https://maps.google.com",
    "github": "https://github.com",
    "netflix": "https://www.netflix.com",
    "spotify": "https://open.spotify.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "facebook": "https://www.facebook.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "twitch": "https://www.twitch.tv",
    "chatgpt": "https://chat.openai.com",
}


class OpenWebsiteTool:
    """Abre un sitio web por nombre conocido, por URL, o busca en Google."""

    name = "abrir_web"
    description = (
        "Abre un sitio web en el navegador. Puede ser un nombre conocido "
        "(gmail, calendario, drive, instagram, youtube, maps, github, whatsapp, "
        "linkedin...), una URL completa, o un dominio. Usala cuando el usuario "
        "diga 'abrí Gmail', 'abrí mi calendario', 'entrá a instagram.com'. "
        "Argumento: 'sitio'."
    )
    risk = RiskLevel.SAFE
    final = True

    def __init__(self, opener: Opener | None = None) -> None:
        self._opener = opener or webbrowser.open

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sitio": {"type": "string", "description": "Nombre del sitio, URL o dominio."}
            },
            "required": ["sitio"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        sitio = str(arguments.get("sitio", "")).strip()
        if not sitio:
            return "¿Qué sitio querés abrir?"

        clave = sitio.lower()
        if clave in _SITIOS:
            self._opener(_SITIOS[clave])
            return f"Abriendo {sitio}. 🌐"

        if clave.startswith(("http://", "https://")):
            self._opener(sitio)
            return f"Abriendo {sitio}. 🌐"

        # Parece un dominio (tiene punto y no espacios): lo abrimos con https.
        if "." in clave and " " not in clave:
            self._opener(f"https://{clave}")
            return f"Abriendo {sitio}. 🌐"

        # No lo reconocimos: lo buscamos en Google.
        q = urllib.parse.quote_plus(sitio)
        self._opener(f"https://www.google.com/search?q={q}")
        return f"No conocía ese sitio, así que busqué '{sitio}' en Google. 🌐"
