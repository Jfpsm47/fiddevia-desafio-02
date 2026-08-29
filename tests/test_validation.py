"""Validação e classificação de registros (RF04, BUG-004, BUG-005)."""
import pytest

from src.validation import is_missing, normalize_category, validate_record

CATS = {
    "categorias_oficiais": [
        {"nome": "Python e bibliotecas", "variacoes": ["python", "pip"]},
        {"nome": "Acesso e senha", "variacoes": ["senha", "acesso"]},
    ]
}

BASE = {
    "protocolo": "AT-001", "data": "01/08/2026", "email": "a@b.com",
    "cep": "78200-000", "categoria": "pip", "tempo_minutos": "20",
    "solicitante": "Ana", "descricao": "Erro",
}


def classificar(**alteracoes):
    registro = {**BASE, **alteracoes}
    return validate_record(registro, CATS)


def test_registro_valido():
    classificacao, motivos, normalizado = classificar()
    assert classificacao == "valido" and not motivos
    assert normalizado["categoria_normalizada"] == "Python e bibliotecas"


def test_email_invalido():
    assert "email_invalido" in classificar(email="invalido")[1]


# --- BUG-004: os documentos marcam campo ausente com o literal [vazio] ---

@pytest.mark.parametrize(
    "marcador",
    ["[vazio]", "[VAZIO]", "", "  ", "N/A", "-", "--", "?", "nao informado"],
)
def test_marcadores_de_ausencia_sao_reconhecidos(marcador):
    assert is_missing(marcador)


def test_valor_real_nao_e_ausencia():
    assert not is_missing("Ana Maria")
    assert not is_missing("0")


def test_solicitante_vazio_nao_pode_passar_como_valido():
    """AT-081 tinha `Solicitante [vazio]` e era classificado como válido."""
    classificacao, motivos, _ = classificar(solicitante="[vazio]")
    assert classificacao == "incompleto"
    assert "solicitante_ausente" in motivos


def test_tempo_vazio_e_ausencia_e_nao_invalidez():
    classificacao, motivos, normalizado = classificar(tempo_minutos="")
    assert classificacao == "incompleto"
    assert "tempo_ausente" in motivos and "tempo_invalido" not in motivos
    assert normalizado["tempo_obj"] is None


# --- BUG-005: precedência entre inválido e incompleto ---

def test_invalido_prevalece_sobre_incompleto():
    """AT-076: e-mail malformado *e* tempo ausente. O erro mais grave manda."""
    classificacao, motivos, _ = classificar(email="email-invalido", tempo_minutos="")
    assert classificacao == "invalido"
    assert "email_invalido" in motivos and "tempo_ausente" in motivos


def test_somente_ausencias_classificam_como_incompleto():
    classificacao, motivos, _ = classificar(solicitante="[vazio]", tempo_minutos="[vazio]")
    assert classificacao == "incompleto"
    assert set(motivos) == {"solicitante_ausente", "tempo_ausente"}


@pytest.mark.parametrize(
    "campo,valor,motivo",
    [
        ("protocolo", "PROTOCOLO?", "protocolo_invalido"),
        ("data", "32/13/2026", "data_invalida"),
        ("email", "email-invalido", "email_invalido"),
        ("cep", "7820", "cep_invalido"),
        ("categoria", "categoria desconhecida", "categoria_invalida"),
        ("tempo_minutos", "-15", "tempo_invalido"),
    ],
)
def test_cada_campo_malformado_gera_invalido(campo, valor, motivo):
    classificacao, motivos, _ = classificar(**{campo: valor})
    assert classificacao == "invalido"
    assert motivo in motivos


@pytest.mark.parametrize(
    "campo", ["protocolo", "data", "email", "cep", "categoria", "tempo_minutos"]
)
def test_cada_campo_ausente_gera_incompleto(campo):
    classificacao, motivos, _ = classificar(**{campo: "[vazio]"})
    assert classificacao == "incompleto"
    assert f"{campo.replace('_minutos', '')}_ausente" in " ".join(motivos)


def test_tempo_negativo_e_invalido_e_nao_e_persistido():
    _, motivos, normalizado = classificar(tempo_minutos="-15")
    assert "tempo_invalido" in motivos and normalizado["tempo_obj"] is None


def test_normalizacao_de_categoria_ignora_caixa_e_acento():
    assert normalize_category("PYTHON", CATS) == "Python e bibliotecas"
    assert normalize_category("  Pip  ", CATS) == "Python e bibliotecas"
    assert normalize_category("categoria desconhecida", CATS) is None
