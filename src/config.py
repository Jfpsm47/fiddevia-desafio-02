"""Carregamento centralizado das configurações e resolução de caminhos."""
from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

SQLITE_PREFIX = "sqlite:///"


def load_config(path: str | Path | None = None) -> dict:
    """Lê o ``config.json`` e as variáveis do ``.env``.

    Args:
        path: caminho alternativo para o arquivo de configuração.

    Returns:
        O dicionário de configuração, acrescido da chave ``_root`` com a raiz
        do projeto.
    """
    load_dotenv(ROOT / ".env")
    target = Path(path) if path else ROOT / "config.json"
    with target.open(encoding="utf-8") as stream:
        cfg = json.load(stream)
    cfg["_root"] = str(ROOT)
    return cfg


def resolve(root: str | Path, relative: str | Path) -> Path:
    """Resolve ``relative`` contra ``root``, preservando caminhos absolutos."""
    path = Path(relative)
    return path if path.is_absolute() else Path(root) / path


def resolve_sqlite_url(root: str | Path, url: str) -> str:
    """Converte uma URL SQLite relativa em absoluta, ancorada em ``root``.

    URLs de outros dialetos, caminhos já absolutos e bancos em memória são
    devolvidos sem alteração.

    Args:
        root: raiz do projeto.
        url: URL de conexão como consta no ``config.json``.

    Returns:
        A URL pronta para ``create_engine``.
    """
    if not url.startswith(SQLITE_PREFIX):
        return url
    remainder = url[len(SQLITE_PREFIX):]
    if not remainder or remainder == ":memory:":
        return url
    if remainder.startswith("/"):
        # sqlite://// — caminho absoluto no padrão POSIX.
        return url
    path = Path(remainder)
    if path.is_absolute():
        return url
    return SQLITE_PREFIX + str(Path(root) / path)
