"""Interfaz de chat por terminal: implementa InterfacePort.

Esta clase es un adaptador de INTERFAZ: traduce entre la terminal y el mundo de
POLO. `receive()` lee texto del teclado; `present()` muestra la respuesta. El
día que hagamos la máscara, será otra clase con estos mismos dos métodos.
"""

from __future__ import annotations

import re

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from polo.core.models import AssistantOutput, MemoryItem, ToolSpec, UserInput
from polo.core.ports.listener import ListenerPort
from polo.core.ports.speech import SpeechPort

# Palabras que terminan la conversación.
_SALIR = {"salir", "chau", "exit", "quit", "adios", "adiós"}


def _para_voz(texto: str) -> str:
    """Limpia símbolos de markdown/emojis para que no se lean en voz alta."""
    # Quita marcadores comunes de markdown (*, #, _, `, >).
    limpio = re.sub(r"[*#_`>]", "", texto)
    # Colapsa espacios múltiples.
    return re.sub(r"\s+", " ", limpio).strip()


class CLIChat:
    """Entrada/salida de POLO a través de la terminal."""

    def __init__(
        self,
        speaker: SpeechPort | None = None,
        listener: ListenerPort | None = None,
    ) -> None:
        self._console = Console()
        # Si hay un speaker, POLO habla sus respuestas además de mostrarlas.
        self._speaker = speaker
        # Si hay un listener, con Enter vacío POLO graba tu voz.
        self._listener = listener

    def receive(self) -> UserInput:
        """Lee la próxima entrada. Con voz activada, Enter vacío grada del micro."""
        if self._listener is not None:
            texto = self._console.input("[bold green]Tú[/bold green] [dim](Enter = hablar)[/dim] ")
            if not texto.strip():
                hablado = self._listener.listen()
                if hablado:
                    self._console.print(f"[dim]🎤 «{hablado}»[/dim]")
                else:
                    self._console.print("[dim]🎤 (no se detectó voz)[/dim]")
                return UserInput(text=hablado)
            return UserInput(text=texto)

        texto = self._console.input("[bold green]Tú[/bold green] ")
        return UserInput(text=texto)

    def present(self, output: AssistantOutput) -> None:
        """Muestra la respuesta de POLO con formato (y la habla si hay voz)."""
        self._console.print(
            Panel(
                Markdown(output.text),
                title="[bold cyan]POLO[/bold cyan]",
                border_style="cyan",
            )
        )
        if self._speaker is not None:
            self._speaker.speak(_para_voz(output.text))

    # ── Utilidades de la interfaz (no forman parte del contrato) ──────────

    def es_salida(self, entrada: UserInput) -> bool:
        """Indica si el usuario quiso terminar la conversación."""
        return entrada.text.strip().lower() in _SALIR

    def saludar(self) -> None:
        self._console.print(
            Panel.fit(
                "Hola, soy [bold cyan]POLO[/bold cyan]. Escribe para conversar.\n"
                "Para salir: escribe 'salir'.",
                border_style="cyan",
            )
        )

    def despedir(self) -> None:
        self._console.print("[dim]Hasta luego.[/dim]")

    def pensando(self) -> None:
        """Aviso estático de que POLO está trabajando.

        Estático a propósito: un spinner animado corre en otro hilo y peleaba con
        los pedidos de confirmación en la terminal (se tragaba tu respuesta). La
        confiabilidad vale más que la animación.
        """
        self._console.print("[dim]🤔 POLO está pensando...[/dim]")

    def error(self, mensaje: str) -> None:
        self._console.print(f"[bold red]⚠ {mensaje}[/bold red]")

    def mostrar_memoria(self, items: list[MemoryItem]) -> None:
        """Muestra todo lo que POLO recuerda."""
        if not items:
            self._console.print("[dim]POLO todavía no recuerda nada de vos.[/dim]")
            return
        lineas = "\n".join(f"• {m.text}  [dim]({m.created_at})[/dim]" for m in items)
        self._console.print(
            Panel(
                lineas,
                title=f"[bold cyan]Memoria de POLO ({len(items)})[/bold cyan]",
                border_style="cyan",
            )
        )

    def confirmar(self, pregunta: str) -> bool:
        """Pide una confirmación sí/no al usuario."""
        resp = self._console.input(f"{pregunta} [bold](s/N)[/bold] ")
        return resp.strip().lower() in {"s", "si", "sí", "y", "yes"}

    def mostrar_error(self, mensaje: str) -> None:
        """Muestra un error de arranque con estilo claro."""
        self._console.print(
            Panel(
                mensaje,
                title="[bold red]No se pudo iniciar POLO[/bold red]",
                border_style="red",
            )
        )

    def confirm(self, prompt: str) -> bool:
        """Implementa ConfirmerPort: el núcleo pide permiso a través de aquí."""
        self._console.print(f"[bold yellow]🔒 {prompt}[/bold yellow]")
        return self.confirmar("¿Autorizás?")

    def mostrar_herramientas(self, specs: list[ToolSpec]) -> None:
        """Lista las herramientas disponibles (incluidas las de plugins)."""
        if not specs:
            self._console.print("[dim]POLO no tiene herramientas cargadas.[/dim]")
            return
        lineas = "\n".join(f"• [bold]{s.name}[/bold]: {s.description}" for s in specs)
        self._console.print(
            Panel(
                lineas,
                title=f"[bold cyan]Herramientas ({len(specs)})[/bold cyan]",
                border_style="cyan",
            )
        )
