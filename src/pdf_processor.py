"""Extração direta de texto e encaminhamento de páginas para OCR."""
from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_pages(path: str | Path, min_chars: int = 40) -> list[dict]:
    """Lê o texto de cada página e decide se ela precisa de OCR.

    Args:
        path: caminho do documento.
        min_chars: mínimo de caracteres para considerar a extração direta
            suficiente. Abaixo disso a página é encaminhada ao OCR.

    Returns:
        Uma entrada por página, com ``pagina``, ``texto`` e ``metodo``
        (``extracao_direta`` ou ``ocr_pendente``).
    """
    reader = PdfReader(str(path))
    pages = []
    for number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        pages.append({
            "pagina": number,
            "texto": text,
            "metodo": "extracao_direta" if len(text) >= min_chars else "ocr_pendente",
        })
    return pages
