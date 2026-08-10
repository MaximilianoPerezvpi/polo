"""Tests de la política de seguridad de rutas sensibles."""

from __future__ import annotations

from pathlib import Path

from polo.adapters.tools.read_file import ReadFileTool
from polo.core.security import is_sensitive_path


def test_bloquea_ssh() -> None:
    assert is_sensitive_path(Path("/home/maxi/.ssh/id_rsa"))


def test_bloquea_env() -> None:
    assert is_sensitive_path(Path("C:/proyecto/.env"))


def test_bloquea_claves_pem_y_key() -> None:
    assert is_sensitive_path(Path("/home/maxi/cert.pem"))
    assert is_sensitive_path(Path("/home/maxi/private.key"))


def test_bloquea_credenciales() -> None:
    assert is_sensitive_path(Path("C:/Users/maxi/credentials/google.json"))


def test_no_bloquea_archivos_normales() -> None:
    assert not is_sensitive_path(Path("C:/Users/maxi/Downloads/foto.jpg"))
    assert not is_sensitive_path(Path("/home/maxi/documento.txt"))


def test_no_hay_falsos_positivos_por_substring() -> None:
    # "tokenizer" NO debe bloquearse solo por contener "token".
    assert not is_sensitive_path(Path("/home/maxi/tokenizer/data.txt"))


def test_read_file_rechaza_sensible(tmp_path: Path) -> None:
    # Creamos un archivo dentro de una carpeta .ssh y verificamos el rechazo.
    ssh = tmp_path / ".ssh"
    ssh.mkdir()
    clave = ssh / "id_rsa"
    clave.write_text("clave-secreta")

    resultado = ReadFileTool().run({"ruta": str(clave)})

    assert "seguridad" in resultado.lower()
    assert "clave-secreta" not in resultado
