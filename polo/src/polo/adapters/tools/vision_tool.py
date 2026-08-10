"""Herramienta de visión: analiza o describe una imagen.

Es una herramienta como cualquier otra (Fase 3), pero por detrás usa un modelo
de visión (VisionPort). Solo lectura, así que es SAFE.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from polo.core.ports.tool import RiskLevel
from polo.core.ports.vision import VisionPort

_PREGUNTA_DEFAULT = "Describe esta imagen en español, con detalle."


class VisionTool:
    """Mira una imagen y responde qué contiene."""

    name = "analizar_imagen"
    description = (
        "Analiza o describe una imagen. Argumentos: 'ruta' (la ruta de la "
        "imagen) y 'pregunta' (qué querés saber sobre ella, opcional)."
    )
    risk = RiskLevel.SAFE

    def __init__(self, vision: VisionPort) -> None:
        self._vision = vision

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ruta": {
                    "type": "string",
                    "description": "Ruta completa de la imagen.",
                },
                "pregunta": {
                    "type": "string",
                    "description": "Qué querés saber sobre la imagen (opcional).",
                },
            },
            "required": ["ruta"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        ruta = str(arguments.get("ruta", "")).strip()
        if not ruta:
            return "Error: no se indicó la ruta de la imagen."

        path = Path(ruta).expanduser()
        if not path.is_file():
            return f"No existe una imagen en '{ruta}'."

        pregunta = str(arguments.get("pregunta") or "").strip() or _PREGUNTA_DEFAULT
        try:
            return self._vision.describe(path, pregunta)
        except Exception as exc:  # noqa: BLE001 - el modelo puede fallar de varias formas
            return f"No pude analizar la imagen: {exc}"
