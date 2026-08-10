"""Puertos: los contratos abstractos del núcleo."""

from polo.core.ports.confirm import ConfirmerPort
from polo.core.ports.embedding import EmbeddingPort
from polo.core.ports.interface import InterfacePort
from polo.core.ports.llm import LLMPort
from polo.core.ports.memory import MemoryPort
from polo.core.ports.plugin import Plugin
from polo.core.ports.speech import SpeechPort
from polo.core.ports.tool import RiskLevel, Tool
from polo.core.ports.vision import VisionPort

__all__ = [
    "ConfirmerPort",
    "EmbeddingPort",
    "InterfacePort",
    "LLMPort",
    "MemoryPort",
    "Plugin",
    "RiskLevel",
    "SpeechPort",
    "Tool",
    "VisionPort",
]
