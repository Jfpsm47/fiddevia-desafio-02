"""Resolução de caminhos e da URL do banco (BUG-001, BUG-029)."""
from pathlib import Path

from src.config import resolve, resolve_sqlite_url

ROOT = Path("/proj")


def test_url_relativa_e_ancorada_na_raiz():
    resultado = resolve_sqlite_url(ROOT, "sqlite:///database/atendimentos.db")
    assert resultado.startswith("sqlite:///")
    assert Path(resultado[len("sqlite:///"):]) == ROOT / "database" / "atendimentos.db"


def test_banco_em_memoria_nao_e_alterado():
    assert resolve_sqlite_url(ROOT, "sqlite:///:memory:") == "sqlite:///:memory:"


def test_outro_dialeto_nao_e_alterado():
    url = "postgresql+psycopg://host/base"
    assert resolve_sqlite_url(ROOT, url) == url


def test_caminho_absoluto_posix_nao_e_alterado():
    url = "sqlite:////var/lib/atendimentos.db"
    assert resolve_sqlite_url(ROOT, url) == url


def test_url_vazia_nao_quebra():
    assert resolve_sqlite_url(ROOT, "sqlite:///") == "sqlite:///"


def test_ramo_morto_com_espaco_nao_e_mais_necessario():
    """A entrega tratava `sqlite:/// ` (com espaço), condição que nunca ocorre."""
    resultado = resolve_sqlite_url(ROOT, "sqlite:///database/a.db")
    assert " " not in resultado[len("sqlite:///"):].replace(str(ROOT), "")


def test_resolve_preserva_absolutos(tmp_path):
    assert resolve(ROOT, tmp_path) == tmp_path
    assert resolve(ROOT, "data/pdfs") == ROOT / "data" / "pdfs"
