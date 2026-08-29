"""Resposta local e montagem de contexto (RF13, RF14, BUG-034)."""
import pytest

from src.rag import LIMIAR_SUFICIENCIA, answer, local_answer, montar_contexto


def fonte(protocolo: str, similaridade: float, conteudo: str = "Erro ao instalar o pip.") -> dict:
    return {
        "protocolo": protocolo, "documento": "atendimentos_digitais.pdf",
        "pagina": 1, "similaridade": similaridade, "conteudo": conteudo,
        "classificacao": "valido",
    }


def test_resposta_local_usa_os_trechos_recuperados():
    """A entrega devolvia sempre o mesmo texto fixo, qualquer que fosse a recuperação: o modo sem.

    chave nunca respondia (BUG-034).
    """
    resultado = local_answer("Como instalar o pip?", [fonte("AT-003", 0.71)])

    assert resultado["sustentada"] is True
    assert "AT-003" in resultado["resposta"]
    assert "Erro ao instalar o pip." in resultado["resposta"]
    assert resultado["modo"] == "recuperacao_local"


def test_resposta_local_cita_todas_as_fontes_relevantes():
    fontes = [fonte(f"AT-00{i}", 0.7 - i / 100) for i in range(1, 4)]
    resposta = local_answer("pergunta", fontes)["resposta"]
    assert all(f["protocolo"] in resposta for f in fontes)


def test_declara_insuficiencia_quando_nada_sustenta():
    """O RF13 exige informar quando os documentos não sustentam a resposta."""
    resultado = local_answer("Receita de bolo", [fonte("AT-003", LIMIAR_SUFICIENCIA - 0.01)])

    assert resultado["sustentada"] is False
    assert "não sustentam" in resultado["resposta"]
    assert resultado["fontes"], "as fontes fracas continuam visíveis para inspeção"


def test_sem_fontes_declara_insuficiencia():
    resultado = local_answer("qualquer coisa", [])
    assert resultado["sustentada"] is False and resultado["fontes"] == []


def test_trecho_longo_e_truncado_sem_cortar_palavra():
    longo = "palavra " * 200
    resposta = local_answer("p", [fonte("AT-001", 0.9, longo)])["resposta"]
    assert "…" in resposta
    assert len(resposta) < 1200


def test_contexto_respeita_o_limite_de_tamanho():
    """O RF13 pede contexto com tamanho controlado."""
    fontes = [fonte(f"AT-{i:03d}", 0.9, "x" * 500) for i in range(20)]
    contexto = montar_contexto(fontes, limite=1200)
    assert len(contexto) <= 1200 + 100
    assert "AT-000" in contexto and "AT-019" not in contexto


def test_sem_chave_de_api_responde_localmente(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert answer("pergunta", [fonte("AT-003", 0.8)])["modo"] == "recuperacao_local"


def test_falha_do_modelo_cai_para_o_modo_local(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "chave-de-teste")
    monkeypatch.setitem(__import__("sys").modules, "langchain_openai", None)

    resultado = answer("pergunta", [fonte("AT-003", 0.8)])

    assert resultado["modo"] == "recuperacao_local"
    assert "aviso" in resultado


def test_chave_presente_mas_sem_fontes_nao_chama_o_modelo(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "chave-de-teste")
    resultado = answer("pergunta", [])
    assert resultado["modo"] == "recuperacao_local" and resultado["sustentada"] is False


@pytest.mark.parametrize("similaridade,sustentada", [(0.9, True), (0.5, True), (0.1, False)])
def test_limiar_de_suficiencia(similaridade, sustentada):
    assert local_answer("p", [fonte("AT-001", similaridade)])["sustentada"] is sustentada
