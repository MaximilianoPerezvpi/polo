"""Errores propios del dominio de POLO.

Vivir aquí (en el núcleo) permite que la interfaz capture problemas sin conocer
detalles del proveedor concreto. Por ejemplo, si Ollama no está corriendo, el
adaptador traduce ese fallo a `LLMUnavailableError`, y la CLI lo maneja sin
importar nunca nada de `ollama`.
"""

from __future__ import annotations


class PoloError(Exception):
    """Base de todos los errores propios de POLO."""


class LLMUnavailableError(PoloError):
    """El motor de lenguaje no está disponible (p. ej. Ollama apagado)."""
