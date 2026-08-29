"""Preparação do banco e operações de consulta (BUG-001)."""
import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")

from src.database import create_session_factory, session_scope  # noqa: E402
from src.models import Documento  # noqa: E402


def test_cria_o_diretorio_do_banco_quando_ausente(tmp_path):
    """Uma cópia limpa do repositório não tem `database/`; o SQLite não o cria."""
    alvo = tmp_path / "database" / "atendimentos.db"
    assert not alvo.parent.exists()

    create_session_factory(f"sqlite:///{alvo.as_posix()}")

    assert alvo.parent.is_dir()
    assert alvo.exists()


def test_diretorio_aninhado_tambem_e_criado(tmp_path):
    alvo = tmp_path / "a" / "b" / "c" / "base.db"
    create_session_factory(f"sqlite:///{alvo.as_posix()}")
    assert alvo.exists()


def test_banco_em_memoria_nao_tenta_criar_diretorio():
    factory = create_session_factory("sqlite:///:memory:")
    with session_scope(factory) as sessao:
        sessao.add(
            Documento(nome_arquivo="a.pdf", hash_sha256="x", total_paginas=1,
                      metodo="extracao_direta")
        )
    assert True
