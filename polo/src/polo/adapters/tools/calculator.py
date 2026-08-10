"""Herramienta calculadora: evalúa expresiones matemáticas de forma SEGURA.

Lección de seguridad de esta fase: JAMÁS usar `eval()` sobre texto que viene
(indirectamente) del modelo o del usuario. `eval("__import__('os').system('...')")`
podría ejecutar cualquier cosa. En su lugar, parseamos la expresión con el módulo
`ast` y solo permitimos números y operaciones aritméticas. Cualquier otra cosa
(nombres, llamadas a funciones, atributos) se rechaza.

Esto muestra el principio: una herramienta valida y limita su propia entrada.
"""

from __future__ import annotations

import ast
import operator
from collections.abc import Callable
from typing import Any

from polo.core.ports.tool import RiskLevel

# Operadores permitidos. Nada más existe para esta herramienta.
_OPERADORES: dict[type[ast.AST], Callable[..., float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluar(nodo: ast.AST) -> float:
    """Evalúa un nodo del árbol sintáctico, permitiendo solo aritmética."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, int | float):
        return float(nodo.value)
    if isinstance(nodo, ast.BinOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar(nodo.left), _evaluar(nodo.right))
    if isinstance(nodo, ast.UnaryOp) and type(nodo.op) in _OPERADORES:
        return _OPERADORES[type(nodo.op)](_evaluar(nodo.operand))
    # Cualquier otra cosa (nombres, funciones, atributos...) se rechaza.
    raise ValueError("Solo se permiten números y operaciones aritméticas básicas.")


class CalculatorTool:
    """Evalúa una expresión aritmética simple, de forma segura."""

    name = "calculadora"
    description = (
        "Evalúa una expresión matemática y devuelve el resultado. "
        "Soporta + - * / // % ** y paréntesis. Ejemplo: '3 * (4 + 5)'."
    )
    risk = RiskLevel.SAFE

    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expresion": {
                    "type": "string",
                    "description": "La expresión matemática a evaluar.",
                }
            },
            "required": ["expresion"],
        }

    def run(self, arguments: dict[str, Any]) -> str:
        expresion = str(arguments.get("expresion", "")).strip()
        if not expresion:
            return "Error: no se dio ninguna expresión."
        try:
            arbol = ast.parse(expresion, mode="eval")
            resultado = _evaluar(arbol.body)
        except (ValueError, SyntaxError, ZeroDivisionError, TypeError) as exc:
            return f"No pude calcular '{expresion}': {exc}"
        # Mostramos entero si es exacto, si no, con decimales.
        if resultado == int(resultado):
            return f"{expresion} = {int(resultado)}"
        return f"{expresion} = {resultado}"
