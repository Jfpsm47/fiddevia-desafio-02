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

    Antes, `api` importava `indexer`, que importa SQLAlchemy no topo: um ambiente sem esse
    pacote abortava a coleta de toda a suíte (BUG-011).
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


# --- códigos HTTP diferenciados (BUG-012) ---

def test_colecao_vazia_devolve_409_com_instrucao(monkeypatch):
    """A entrega convertia qualquer falha em 503 e descartava a causa."""
    from src.indexer import ColecaoVazia

    def sem_indice(*args, **kwargs):
        raise ColecaoVazia("Nenhum chunk indexado. Execute `python -m src.main --indexar`.")

    monkeypatch.setattr("src.indexer.semantic_query", sem_indice)
    resposta = TestClient(app).post("/ask", json={"pergunta": "instalacao do python"})

    assert resposta.status_code == 409
    assert "--indexar" in resposta.json()["detail"], "a mensagem precisa ser acionável"


def test_dependencia_ausente_devolve_503_nomeando_o_pacote(monkeypatch):
    def sem_dependencia(*args, **kwargs):
        raise ImportError("No module named 'chromadb'", name="chromadb")

    monkeypatch.setattr("src.indexer.semantic_query", sem_dependencia)
    resposta = TestClient(app).post("/ask", json={"pergunta": "instalacao do python"})

    assert resposta.status_code == 503
    assert "chromadb" in resposta.json()["detail"]


def test_falha_inesperada_devolve_500(monkeypatch):
    def explode(*args, **kwargs):
        raise ValueError("algo imprevisto")

    monkeypatch.setattr("src.indexer.semantic_query", explode)
    resposta = TestClient(app).post("/ask", json={"pergunta": "instalacao do python"})

    assert resposta.status_code == 500
    assert "ValueError" in resposta.json()["detail"]


def test_falha_inesperada_e_registrada_em_log(monkeypatch, caplog):
    """A exceção original era descartada sem chegar a nenhum log."""
    def explode(*args, **kwargs):
        raise ValueError("algo imprevisto")

    monkeypatch.setattr("src.indexer.semantic_query", explode)
    with caplog.at_level("ERROR"):
        TestClient(app).post("/ask", json={"pergunta": "instalacao do python"})

    rastreamentos = [r.exc_text for r in caplog.records if r.exc_text]
    assert any("algo imprevisto" in texto for texto in rastreamentos)


def test_resposta_traz_fontes_e_modo(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def recuperar(cfg, pergunta, top_k, categoria=None, incluir_rejeitados=False):
        return [{"protocolo": "AT-003", "documento": "d.pdf", "pagina": 1,
                 "similaridade": 0.8, "conteudo": "pip nao reconhecido",
                 "classificacao": "valido"}]

    monkeypatch.setattr("src.indexer.semantic_query", recuperar)
    dados = TestClient(app).post("/ask", json={"pergunta": "erro de pip"}).json()

    assert dados["modo"] == "recuperacao_local"
    assert dados["fontes"][0]["protocolo"] == "AT-003"
    assert "AT-003" in dados["resposta"]


def test_incluir_rejeitados_chega_a_camada_de_consulta(monkeypatch):
    recebido = {}

    def recuperar(cfg, pergunta, top_k, categoria=None, incluir_rejeitados=False):
        recebido["incluir_rejeitados"] = incluir_rejeitados
        return []

    monkeypatch.setattr("src.indexer.semantic_query", recuperar)
    TestClient(app).post("/ask", json={"pergunta": "erro de pip", "incluir_rejeitados": True})

    assert recebido["incluir_rejeitados"] is True
