"""Tests de la salida de voz (con un speaker falso, sin audio real)."""

from __future__ import annotations

from unittest.mock import MagicMock

from polo.adapters.speech.pyttsx_speaker import PyttsxSpeaker
from polo.core.models import AssistantOutput
from polo.interfaces.cli.chat import CLIChat, _para_voz


class SpeakerFalso:
    """Registra lo que se le pidió decir, sin reproducir audio."""

    def __init__(self) -> None:
        self.dicho: list[str] = []

    def speak(self, text: str) -> None:
        self.dicho.append(text)


def test_cli_sin_speaker_no_habla() -> None:
    # Sin speaker, present() solo muestra texto (no debe fallar).
    cli = CLIChat(speaker=None)
    cli.present(AssistantOutput(text="hola"))  # no explota


def test_cli_con_speaker_habla() -> None:
    speaker = SpeakerFalso()
    cli = CLIChat(speaker=speaker)

    cli.present(AssistantOutput(text="hola mundo"))

    assert speaker.dicho == ["hola mundo"]


def test_para_voz_limpia_markdown() -> None:
    sucio = "**Hola** _mundo_ `código` # título"
    limpio = _para_voz(sucio)
    assert "*" not in limpio
    assert "#" not in limpio
    assert "`" not in limpio
    assert "Hola" in limpio and "mundo" in limpio


def test_pyttsx_speaker_usa_el_engine() -> None:
    # Inyectamos una fábrica que devuelve un engine falso: probamos la lógica
    # sin audio real, y verificamos que se crea un engine por locución.
    engine = MagicMock()
    speaker = PyttsxSpeaker(engine_factory=lambda: engine)

    speaker.speak("probando")

    engine.say.assert_called_once_with("probando")
    engine.runAndWait.assert_called_once()


def test_pyttsx_speaker_crea_engine_fresco_cada_vez() -> None:
    # Cada speak() debe pedir un engine nuevo a la fábrica (evita el bug de
    # "solo habla la primera vez").
    creados: list[MagicMock] = []

    def factory() -> MagicMock:
        m = MagicMock()
        creados.append(m)
        return m

    speaker = PyttsxSpeaker(engine_factory=factory)
    speaker.speak("uno")
    speaker.speak("dos")

    assert len(creados) == 2  # un engine por locución


def test_kokoro_genera_y_reproduce() -> None:
    # Engine falso que devuelve muestras + sample rate; reproductor que registra.
    import numpy as np

    from polo.adapters.speech.kokoro_speaker import KokoroSpeaker

    engine = MagicMock()
    engine.create.return_value = (np.zeros(10, dtype=np.float32), 24000)
    reproducido: list[int] = []

    speaker = KokoroSpeaker(
        voice="ef_dora",
        lang="es",
        engine=engine,
        player=lambda samples, sr: reproducido.append(sr),
    )
    speaker.speak("hola")

    # Se llamó a create con la voz e idioma correctos, y se reprodujo a 24kHz.
    _, kwargs = engine.create.call_args
    assert kwargs["voice"] == "ef_dora"
    assert kwargs["lang"] == "es"
    assert reproducido == [24000]


def test_kokoro_voz_invalida_usa_una_valida() -> None:
    # Si la voz pedida no existe, debe usar una disponible en español, no crashear.
    import numpy as np

    from polo.adapters.speech.kokoro_speaker import KokoroSpeaker

    engine = MagicMock()
    engine.voices = ["ef_dora", "em_alex", "em_santa"]
    engine.create.return_value = (np.zeros(10, dtype=np.float32), 24000)

    speaker = KokoroSpeaker(voice="ef_alex", engine=engine, player=lambda s, sr: None)
    speaker.speak("hola")

    # Debe haber usado una voz válida (ef_dora), no la inexistente ef_alex.
    _, kwargs = engine.create.call_args
    assert kwargs["voice"] == "ef_dora"


def test_kokoro_speak_no_crashea_si_falla() -> None:
    # Si create() explota, speak() no debe propagar la excepción.
    from polo.adapters.speech.kokoro_speaker import KokoroSpeaker

    engine = MagicMock()
    engine.voices = ["ef_dora"]
    engine.create.side_effect = RuntimeError("boom")

    speaker = KokoroSpeaker(voice="ef_dora", engine=engine, player=lambda s, sr: None)
    speaker.speak("hola")  # no debe lanzar
