"""Extração estruturada dos formulários digitalizados (BUG-032)."""
import json
from pathlib import Path

import pytest

pytest.importorskip("numpy")
pytest.importorskip("PIL")

from PIL import Image, ImageDraw  # noqa: E402

from src.ocr_table import (  # noqa: E402
    BORDAS_ESPERADAS,
    nome_plausivel,
    detectar_grade,
    normalizar_cep,
    normalizar_data,
    normalizar_tempo,
    semelhante,
)

PROJETO = Path(__file__).resolve().parents[1]
DIGITALIZADO = PROJETO / "data" / "pdfs" / "atendimentos_digitalizados.pdf"
CATEGORIAS = json.loads(
    (PROJETO / "data" / "auxiliares" / "categorias.json").read_text(encoding="utf-8")
)


def formulario_sintetico(quantidade: int = 2) -> Image.Image:
    """Desenha uma tabela com a mesma geometria do documento oficial."""
    largura, altura = 1241, 1754
    imagem = Image.new("RGB", (largura, altura), "white")
    desenho = ImageDraw.Draw(imagem)
    colunas = [118, 265, 661, 779, 1122]
    topo = 227
    for _ in range(quantidade):
        linhas = [topo + 30 * i for i in range(5)] + [topo + 150, topo + 185, topo + 220]
        for y in linhas:
            desenho.line([(colunas[0], y), (colunas[-1], y)], fill="black", width=2)
        for x in colunas:
            desenho.line([(x, linhas[0]), (x, linhas[4])], fill="black", width=2)
        desenho.line([(colunas[0], linhas[4]), (colunas[0], linhas[-1])], fill="black", width=2)
        desenho.line([(colunas[-1], linhas[4]), (colunas[-1], linhas[-1])], fill="black", width=2)
        topo = linhas[-1] + 19
    return imagem


# --- detecção da grade, sem depender do Tesseract ---

@pytest.mark.parametrize("quantidade", [1, 2, 4])
def test_grade_encontra_todos_os_registros(quantidade):
    registros, colunas = detectar_grade(formulario_sintetico(quantidade))
    assert len(registros) == quantidade
    assert len(colunas) == BORDAS_ESPERADAS
    assert all(len(linhas) == 8 for linhas in registros), "sete faixas por formulário"


def test_grade_de_pagina_esparsa_nao_ganha_coluna_extra():
    """Uma página com um só registro produzia um pico espúrio que desalinhava
    as faixas e fazia os campos da coluna direita serem lidos do rótulo."""
    imagem = formulario_sintetico(1)
    desenho = ImageDraw.Draw(imagem)
    # texto alinhado em uma coluna qualquer, como acontece na página real
    desenho.line([(491, 300), (491, 380)], fill="black", width=2)

    _, colunas = detectar_grade(imagem)

    assert len(colunas) == BORDAS_ESPERADAS
    assert 491 not in colunas


def test_pagina_em_branco_nao_produz_registros():
    registros, _ = detectar_grade(Image.new("RGB", (1241, 1754), "white"))
    assert registros == []


# --- normalizações do texto reconhecido ---

@pytest.mark.parametrize(
    "lido,esperado",
    [
        ("0107/2026", "01/07/2026"),
        ("01072026", "01/07/2026"),
        ("2026-08-17", "2026-08-17"),
        ("20260817", "2026-08-17"),
        ("2026-0847", "2026-08-47"),
        ("nada", "nada"),
    ],
)
def test_normalizar_data(lido, esperado):
    assert normalizar_data(lido) == esperado


@pytest.mark.parametrize(
    "lido,esperado",
    [
        ("78205-160 -CaceresM T", "78205-160"),
        ("78110-000 - Varzea G randeM T", "78110-000"),
        ("78205 160 - Caceres", "78205-160"),
        ("sem cep", "sem cep"),
    ],
)
def test_normalizar_cep(lido, esperado):
    assert normalizar_cep(lido) == esperado


@pytest.mark.parametrize("lido,esperado", [("53mh", "53"), ("60mn", "60"), ("-15 min", "-15"), ("", "")])
def test_normalizar_tempo(lido, esperado):
    assert normalizar_tempo(lido) == esperado


# --- aproximação conservadora ao vocabulário oficial ---

def test_valor_degradado_encontra_o_oficial():
    assert semelhante("atvidade", ["atividade", "software"]) == "atividade"
    assert semelhante("sofware", ["atividade", "software"]) == "software"
    assert semelhante("Concliio", ["Concluido", "Pendente", "Em atendimento"]) == "Concluido"
    assert semelhante("Conclixo", ["Concluido", "Pendente", "Em atendimento"]) == "Concluido"
    assert semelhante("Ematendmento", ["Concluido", "Pendente", "Em atendimento"]) == "Em atendimento"


@pytest.mark.parametrize(
    "lido,plausivel",
    [
        ("Henrique Oliveira Luz", True),
        ("Ana Maria", True),
        ("HenrgueOlveiraLuz", False),
        ("VnkisMendesSaks", False),
        ("", False),
        ("A B", False),
    ],
)
def test_nome_sem_separacao_nao_e_aproveitado(lido, plausivel):
    """A digitalização perde os espaços; o resultado não identifica ninguém."""
    assert nome_plausivel(lido) is plausivel


def test_valor_irreconhecivel_nao_recebe_palpite():
    """Abaixo do corte, o valor é declarado ilegível em vez de ser adivinhado."""
    assert semelhante("xkqz", ["atividade", "software"]) is None
    assert semelhante("", ["atividade"]) is None


# --- integração com o documento oficial ---

pytestmark_ocr = pytest.mark.skipif(not DIGITALIZADO.exists(), reason="PDF oficial ausente")


@pytestmark_ocr
def test_grade_do_documento_oficial_acha_os_25_registros():
    from src.ocr_processor import imagem_da_pagina

    total = 0
    for numero in range(1, 8):
        registros, colunas = detectar_grade(imagem_da_pagina(DIGITALIZADO, numero))
        assert len(colunas) == BORDAS_ESPERADAS, f"página {numero}"
        total += len(registros)
    assert total == 25, "o documento declara 25 registros no próprio cabeçalho"


@pytestmark_ocr
def test_protocolo_so_e_aceito_quando_as_passadas_concordam():
    """Um protocolo errado vira a identidade do registro: sem unanimidade entre
    as passadas de OCR, ele é declarado ilegível em vez de arriscado."""
    pytest.importorskip("pytesseract")
    from src.ocr_processor import imagem_da_pagina, verificar_ocr
    from src.ocr_table import extrair_registros

    disponivel, motivo = verificar_ocr(None, "por")
    if not disponivel:
        pytest.skip(motivo)

    registros = extrair_registros(imagem_da_pagina(DIGITALIZADO, 1), CATEGORIAS)

    assert len(registros) == 4
    for registro in registros:
        protocolo = registro["campos"]["protocolo"]
        if protocolo:
            assert protocolo.startswith("AT-0"), "nenhum protocolo aceito pode estar errado"
            assert "protocolo" not in registro["ilegiveis"]
        else:
            assert "protocolo" in registro["ilegiveis"]


@pytestmark_ocr
def test_email_ilegivel_nunca_e_inventado():
    pytest.importorskip("pytesseract")
    from src.ocr_processor import imagem_da_pagina, verificar_ocr
    from src.ocr_table import extrair_registros

    disponivel, motivo = verificar_ocr(None, "por")
    if not disponivel:
        pytest.skip(motivo)

    registros = extrair_registros(imagem_da_pagina(DIGITALIZADO, 1), CATEGORIAS)

    for registro in registros:
        assert registro["campos"]["email"] == ""
        assert "email" in registro["ilegiveis"]
