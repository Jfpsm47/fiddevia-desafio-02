"""OCR das páginas digitalizadas.

A entrega rasterizava cada página com ``pdf2image``, que exige o binário
**Poppler** — dependência de sistema pesada e não verificada, cuja ausência
descartava 25 registros em silêncio (BUG-002).

Aqui a imagem é lida direto do PDF com ``pypdf``: nos documentos deste desafio
cada página digitalizada carrega exatamente um JPEG, o que dispensa o Poppler e
a rasterização. ``pdf2image`` fica como alternativa para PDFs cuja página não
seja uma imagem única.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

CAMINHOS_PADRAO_WINDOWS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


def configurar_tesseract(tesseract_cmd: str | None = None) -> str | None:
    """Aponta o ``pytesseract`` para o executável do Tesseract.

    Args:
        tesseract_cmd: caminho explícito, vindo de ``config.json`` ou do
            ambiente. Quando vazio, procura no ``PATH`` e, no Windows, nos
            locais de instalação padrão — o instalador oficial não acrescenta o
            Tesseract ao ``PATH``.

    Returns:
        O caminho configurado, ou ``None`` se nada foi encontrado.
    """
    import pytesseract

    candidatos = [tesseract_cmd] if tesseract_cmd else []
    candidatos.extend(CAMINHOS_PADRAO_WINDOWS)
    for candidato in candidatos:
        if candidato and Path(candidato).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidato
            return candidato
    return None


@lru_cache(maxsize=4)
def verificar_ocr(tesseract_cmd: str | None = None, idioma: str = "por") -> tuple[bool, str]:
    """Verifica, antes de processar, se o OCR está utilizável.

    Returns:
        Um par ``(disponivel, mensagem)``. A mensagem é acionável: diz o que
        instalar ou configurar, em vez de deixar a falha aparecer página a
        página no meio do processamento.
    """
    try:
        import pytesseract
    except ImportError:
        return False, "pytesseract não está instalado: execute `pip install -r requirements.txt`."

    configurar_tesseract(tesseract_cmd)
    try:
        versao = pytesseract.get_tesseract_version()
    except Exception:
        return False, (
            "Tesseract não encontrado. Instale-o (Windows: "
            "`winget install -e --id UB-Mannheim.TesseractOCR`) e, se ele não estiver "
            "no PATH, informe o caminho em config.json → ocr.tesseract_cmd."
        )

    try:
        idiomas = set(pytesseract.get_languages(config=""))
    except Exception:
        idiomas = set()
    if idiomas and idioma not in idiomas:
        return False, (
            f"Tesseract {versao} encontrado, mas sem o idioma '{idioma}'. "
            f"Disponíveis: {sorted(idiomas)}. Instale o pacote de idioma correspondente."
        )
    return True, f"Tesseract {versao} pronto (idioma '{idioma}')."


def imagem_da_pagina(pdf_path: str | Path, page_number: int, dpi: int = 300) -> Any:
    """Devolve a imagem de uma página, para OCR.

    Tenta primeiro a imagem embutida no PDF, que preserva a resolução original
    e não depende do Poppler. Só recorre à rasterização quando a página não é
    uma imagem única.

    Args:
        pdf_path: caminho do documento.
        page_number: número da página, começando em 1.
        dpi: resolução usada apenas no caminho alternativo de rasterização.

    Returns:
        Um objeto ``PIL.Image``, ou ``None`` se a página não pôde ser obtida.
    """
    from pypdf import PdfReader

    pagina = PdfReader(str(pdf_path)).pages[page_number - 1]
    imagens = list(pagina.images)
    if len(imagens) == 1:
        return imagens[0].image

    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise RuntimeError(
            "A página não é uma imagem única e o pdf2image não está instalado "
            "para rasterizá-la."
        ) from exc
    convertidas = convert_from_path(
        str(pdf_path), dpi=dpi, first_page=page_number, last_page=page_number
    )
    return convertidas[0] if convertidas else None


def ocr_page(
    pdf_path: str | Path,
    page_number: int,
    dpi: int = 300,
    language: str = "por",
    tesseract_cmd: str | None = None,
) -> str:
    """Executa OCR em uma página e devolve o texto bruto.

    Args:
        pdf_path: caminho do documento.
        page_number: número da página, começando em 1.
        dpi: resolução do caminho alternativo de rasterização.
        language: idioma do Tesseract.
        tesseract_cmd: caminho do executável, quando fora do ``PATH``.

    Returns:
        O texto reconhecido, ou string vazia se a página não produziu imagem.
    """
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("Instale pytesseract para executar OCR") from exc

    configurar_tesseract(tesseract_cmd)
    imagem = imagem_da_pagina(pdf_path, page_number, dpi)
    if imagem is None:
        return ""
    try:
        return pytesseract.image_to_string(imagem, lang=language)
    except pytesseract.TesseractError:
        logging.warning(
            "Idioma '%s' indisponível na página %s; usando 'eng'.", language, page_number
        )
        return pytesseract.image_to_string(imagem, lang="eng")
