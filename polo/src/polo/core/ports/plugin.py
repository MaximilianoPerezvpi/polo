"""Puerto Plugin: el contrato de una habilidad que POLO puede aprender.

Un plugin aporta herramientas (y en el futuro podría aportar más cosas). POLO lo
descubre, lo carga, y suma sus herramientas a las que ya tiene, sin que haya que
tocar el núcleo ni la lista de herramientas en el arranque.

Un archivo de plugin define un objeto llamado `PLUGIN` que cumple este contrato.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from polo.core.ports.tool import Tool


@runtime_checkable
class Plugin(Protocol):
    """Una habilidad cargable de POLO."""

    @property
    def name(self) -> str:
        """Nombre del plugin."""
        ...

    @property
    def version(self) -> str:
        """Versión del plugin (ej: '1.0.0')."""
        ...

    def tools(self) -> list[Tool]:
        """Las herramientas que este plugin aporta."""
        ...
