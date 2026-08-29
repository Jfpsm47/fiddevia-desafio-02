"""Extração direta e encaminhamento ao OCR (RF02).

Arquivo previsto na estrutura do enunciado e ausente da entrega (BUG-030).
"""
from pathlib import Path

import pytest

pytest.importorskip("pypdf")

from src.pdf_processor import extract_pdf_pages  # noqa: E402

PROJETO = Path(__file__).resolve().parents[1]
PDFS = PROJETO / "data" / "pdfs"
DIGITAIS = PDFS / "atendimentos_digitais.pdf"
DIGITALIZADO = PDFS / "atendimentos_digitalizados.pdf"

pytestmark = pytest.mark.skipif(not PDFS.is_dir(), reason="PDFs oficiais ausentes")


def test_paginas_com_texto_sao_marcadas_para_extracao_direta():
    paginas = extract_pdf_pages(DIGITAIS)

    assert len(paginas) == 13
    assert {p["metodo"] for p in paginas} == {"extracao_direta"}
    assert all(p["texto"] for p in paginas)


def test_paginas_sem_texto_sao_encaminhadas_ao_ocr():
    """O documento escaneado não tem camada de texto em nenhuma página."""
    paginas = extract_pdf_pages(DIGITALIZADO)

    assert len(paginas) == 7
    assert {p["metodo"] for p in paginas} == {"ocr_pendente"}


def test_numeracao_das_paginas_comeca_em_um():
    paginas = extract_pdf_pages(DIGITAIS)
    assert [p["pagina"] for p in paginas] == list(range(1, 14))


def test_limiar_de_caracteres_decide_o_encaminhamento():
    """Acima do limiar a extração direta basta; abaixo, a página vai ao OCR."""
    baixo = extract_pdf_pages(DIGITAIS, min_chars=1)
    alto = extract_pdf_pages(DIGITAIS, min_chars=10_000)

    assert {p["metodo"] for p in baixo} == {"extracao_direta"}
    assert {p["metodo"] for p in alto} == {"ocr_pendente"}
    assert [p["texto"] for p in baixo] == [p["texto"] for p in alto], "o texto lido não muda"


def test_todas_as_paginas_declaram_as_tres_chaves():
    for pagina in extract_pdf_pages(DIGITAIS):
        assert set(pagina) == {"pagina", "texto", "metodo"}


def test_documento_ilegivel_propaga_o_erro(tmp_path):
    """Cabe ao pipeline decidir o que fazer; aqui a falha não é silenciada."""
    corrompido = tmp_path / "corrompido.pdf"
    corrompido.write_bytes(b"isto nao e um PDF")

    with pytest.raises(Exception):  # noqa: B017 - pypdf varia o tipo conforme o dano
        extract_pdf_pages(corrompido)


def test_o_documento_digitalizado_tem_uma_imagem_por_pagina():
    """É o que permite ler a página sem Poppler (BUG-002)."""
    from pypdf import PdfReader

    for pagina in PdfReader(str(DIGITALIZADO)).pages:
        assert len(list(pagina.images)) == 1
