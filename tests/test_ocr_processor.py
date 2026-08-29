"""Leitura das páginas digitalizadas (RF03, BUG-002)."""
from pathlib import Path

import pytest

pytest.importorskip("pypdf")

from src.ocr_processor import configurar_tesseract, imagem_da_pagina, verificar_ocr  # noqa: E402

PROJETO = Path(__file__).resolve().parents[1]
DIGITALIZADO = PROJETO / "data" / "pdfs" / "atendimentos_digitalizados.pdf"
DIGITAL = PROJETO / "data" / "pdfs" / "atendimentos_digitais.pdf"


@pytest.mark.skipif(not DIGITALIZADO.exists(), reason="PDF oficial ausente")
def test_imagem_vem_do_pdf_sem_rasterizar(monkeypatch):
    """A imagem embutida dispensa o Poppler, cuja ausência custava 25 registros."""
    def sem_poppler(*args, **kwargs):
        raise AssertionError("pdf2image não deveria ser chamado para uma página de imagem única")

    monkeypatch.setattr("pdf2image.convert_from_path", sem_poppler, raising=False)

    imagem = imagem_da_pagina(DIGITALIZADO, 1)

    assert imagem is not None
    assert imagem.size == (1241, 1754), "resolução original preservada, sem reamostrar"


@pytest.mark.skipif(not DIGITALIZADO.exists(), reason="PDF oficial ausente")
def test_todas_as_paginas_digitalizadas_produzem_imagem():
    for numero in range(1, 8):
        assert imagem_da_pagina(DIGITALIZADO, numero) is not None


@pytest.mark.skipif(not DIGITAL.exists(), reason="PDF oficial ausente")
def test_pagina_sem_imagem_unica_exige_rasterizacao():
    """Páginas de texto não têm uma imagem única; o caminho alternativo assume."""
    with pytest.raises(Exception):
        imagem_da_pagina(DIGITAL, 1)


def test_verificacao_avisa_quando_o_tesseract_nao_e_encontrado(monkeypatch):
    """A falha precisa aparecer antes do processamento, com instrução acionável."""
    import pytesseract

    verificar_ocr.cache_clear()

    def sem_tesseract():
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, "get_tesseract_version", sem_tesseract)
    monkeypatch.setattr("src.ocr_processor.CAMINHOS_PADRAO_WINDOWS", ())

    disponivel, mensagem = verificar_ocr("/caminho/inexistente/tesseract.exe", "por")

    verificar_ocr.cache_clear()
    assert not disponivel
    assert "config.json" in mensagem and "tesseract_cmd" in mensagem


def test_verificacao_avisa_quando_falta_o_idioma(monkeypatch):
    import pytesseract

    verificar_ocr.cache_clear()
    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: "5.5.3")
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "osd"])

    disponivel, mensagem = verificar_ocr(None, "por")

    verificar_ocr.cache_clear()
    assert not disponivel and "'por'" in mensagem


def test_caminho_inexistente_e_sem_padrao_devolve_nada(monkeypatch):
    monkeypatch.setattr("src.ocr_processor.CAMINHOS_PADRAO_WINDOWS", ())
    assert configurar_tesseract("/nao/existe/tesseract.exe") is None


def test_encontra_o_tesseract_nos_locais_padrao_do_windows(monkeypatch, tmp_path):
    """O instalador oficial não acrescenta o Tesseract ao PATH."""
    falso = tmp_path / "tesseract.exe"
    falso.write_text("", encoding="utf-8")
    monkeypatch.setattr("src.ocr_processor.CAMINHOS_PADRAO_WINDOWS", (str(falso),))

    assert configurar_tesseract(None) == str(falso)


def test_caminho_explicito_tem_precedencia(monkeypatch, tmp_path):
    explicito = tmp_path / "meu-tesseract.exe"
    explicito.write_text("", encoding="utf-8")
    padrao = tmp_path / "padrao.exe"
    padrao.write_text("", encoding="utf-8")
    monkeypatch.setattr("src.ocr_processor.CAMINHOS_PADRAO_WINDOWS", (str(padrao),))

    assert configurar_tesseract(str(explicito)) == str(explicito)
