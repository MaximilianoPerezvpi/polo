"""Tests de la herramienta de visión (con un VisionPort falso, sin modelo real)."""

from __future__ import annotations

from pathlib import Path

from polo.adapters.tools.vision_tool import VisionTool
from polo.core.ports.tool import RiskLevel


class VisionFalso:
    """VisionPort falso: registra lo que recibió y responde fijo."""

    def __init__(self, respuesta: str = "una foto de un gato") -> None:
        self.respuesta = respuesta
        self.ultima_pregunta = ""
        self.ultima_ruta: Path | None = None

    def describe(self, image_path: Path, question: str) -> str:
        self.ultima_ruta = image_path
        self.ultima_pregunta = question
        return self.respuesta


def test_analiza_imagen_existente(tmp_path: Path) -> None:
    img = tmp_path / "foto.png"
    img.write_bytes(b"datos-falsos-de-imagen")
    vision = VisionFalso(respuesta="se ve un perro")

    tool = VisionTool(vision=vision)
    resultado = tool.run({"ruta": str(img), "pregunta": "¿qué animal es?"})

    assert resultado == "se ve un perro"
    assert vision.ultima_pregunta == "¿qué animal es?"


def test_usa_pregunta_default_si_no_se_da(tmp_path: Path) -> None:
    img = tmp_path / "foto.png"
    img.write_bytes(b"x")
    vision = VisionFalso()

    VisionTool(vision=vision).run({"ruta": str(img)})

    # Sin pregunta, debe usar la de descripción por defecto.
    assert "describe" in vision.ultima_pregunta.lower()


def test_imagen_inexistente() -> None:
    resultado = VisionTool(vision=VisionFalso()).run({"ruta": "/no/existe.png"})
    assert "no existe" in resultado.lower()


def test_error_del_modelo_no_rompe(tmp_path: Path) -> None:
    img = tmp_path / "foto.png"
    img.write_bytes(b"x")

    class VisionRoto:
        def describe(self, image_path: Path, question: str) -> str:
            raise RuntimeError("modelo caído")

    resultado = VisionTool(vision=VisionRoto()).run({"ruta": str(img)})
    assert "no pude analizar" in resultado.lower()


def test_vision_es_segura() -> None:
    assert VisionTool(vision=VisionFalso()).risk is RiskLevel.SAFE
