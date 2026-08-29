"""Consulta de CEP tolerante a falhas (RF07)."""
import pytest
import requests

from src.cep_client import lookup_cep

BASE = "https://viacep.com.br/ws"

RESPOSTA_OK = {
    "cep": "78005-000", "logradouro": "Rua Engenheiro Ricardo Franco",
    "localidade": "Cuiabá", "uf": "MT", "bairro": "Centro-Norte",
}


class RespostaFalsa:
    """Resposta mínima compatível com o que o cliente usa."""

    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        if self._payload is None:
            raise ValueError("resposta não é JSON")
        return self._payload


@pytest.fixture
def responder(monkeypatch):
    def instalar(resultado):
        def get(url, **kwargs):
            if isinstance(resultado, Exception):
                raise resultado
            instalar.url = url
            instalar.kwargs = kwargs
            return resultado

        monkeypatch.setattr(requests, "get", get)

    return instalar


def test_cep_resolvido_devolve_municipio_e_uf(responder):
    responder(RespostaFalsa(RESPOSTA_OK))
    assert lookup_cep("78005-000", BASE) == {
        "municipio": "Cuiabá", "uf": "MT", "logradouro": "Rua Engenheiro Ricardo Franco",
    }


def test_separadores_do_cep_sao_ignorados(responder):
    responder(RespostaFalsa(RESPOSTA_OK))
    lookup_cep("78.005-000", BASE)
    assert "78005000" in responder.url


@pytest.mark.parametrize("cep", ["7820", "", "abcdefgh", "780050000"])
def test_cep_malformado_nem_chega_a_consultar(cep, monkeypatch):
    def nao_deveria(*args, **kwargs):
        raise AssertionError("nenhuma requisição deveria sair")

    monkeypatch.setattr(requests, "get", nao_deveria)
    assert lookup_cep(cep, BASE) is None


def test_cep_inexistente_devolve_nada(responder):
    """O ViaCEP responde 200 com {"erro": "true"} para CEP que não existe."""
    responder(RespostaFalsa({"erro": "true"}))
    assert lookup_cep("78550-000", BASE) is None


@pytest.mark.parametrize(
    "falha",
    [
        requests.ConnectionError("rede indisponível"),
        requests.Timeout("estourou o tempo"),
        requests.HTTPError("500"),
    ],
)
def test_falha_de_rede_nao_propaga(responder, falha):
    """O enriquecimento é complementar: não pode interromper o pipeline."""
    responder(falha)
    assert lookup_cep("78005-000", BASE) is None


def test_resposta_ilegivel_nao_propaga(responder):
    responder(RespostaFalsa(None))
    assert lookup_cep("78005-000", BASE) is None


def test_erro_http_nao_propaga(responder):
    responder(RespostaFalsa({}, status=503))
    assert lookup_cep("78005-000", BASE) is None


def test_timeout_e_repassado(responder):
    responder(RespostaFalsa(RESPOSTA_OK))
    lookup_cep("78005-000", BASE, timeout=3)
    assert responder.kwargs["timeout"] == 3


def test_log_nao_registra_o_endereco(responder, caplog):
    """A resposta traz dados de endereço; eles não vão para o log."""
    responder(requests.ConnectionError("falha em viacep.com.br/78005000"))
    with caplog.at_level("WARNING"):
        lookup_cep("78005-000", BASE)
    assert "78005000" not in caplog.text
