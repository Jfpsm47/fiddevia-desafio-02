"""Contratos da API HTTP (RF15) e desacoplamento do import (BUG-011)."""
import importlib
import sys

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from src.api import app  # noqa: E402


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200 and response.json()["status"] == "ok"


def test_ask_validation():
    response = TestClient(app).post("/ask", json={"pergunta": "x"})
    assert response.status_code == 422


def test_ask_exige_pergunta():
    assert TestClient(app).post("/ask", json={"top_k": 3}).status_code == 422


def test_ask_limita_top_k():
    resposta = TestClient(app).post("/ask", json={"pergunta": "instalacao", "top_k": 99})
    assert resposta.status_code == 422


def test_modulo_da_api_nao_depende_de_sqlalchemy_para_ser_importado(monkeypatch):
    """A API precisa subir e responder /health sem a camada de persistência.

    Antes, `api` importava `indexer`, que importa SQLAlchemy no topo: um
    ambiente sem esse pacote abortava a coleta de toda a suíte (BUG-011).
    """
    for nome in [m for m in sys.modules if m.startswith(("src.api", "src.indexer", "sqlalchemy"))]:
        monkeypatch.delitem(sys.modules, nome, raising=False)

    real_import = __import__

    def sem_sqlalchemy(name, *args, **kwargs):
        if name == "sqlalchemy" or name.startswith("sqlalchemy."):
            raise ModuleNotFoundError("No module named 'sqlalchemy'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", sem_sqlalchemy)
    modulo = importlib.import_module("src.api")

    assert TestClient(modulo.app).get("/health").status_code == 200
