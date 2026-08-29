"""Orquestração do processamento ponta a ponta."""
from __future__ import annotations

import json
import logging
import re
import sys
from hashlib import sha256
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .analytics import export_results, generate_charts
from .config import resolve, resolve_sqlite_url
from .database import create_session_factory, find_by_protocol, session_scope
from .models import Atendimento, Chunk, Documento, ErroProcessamento
from .ocr_processor import imagem_da_pagina, verificar_ocr
from .ocr_table import extrair_registros
from .pdf_processor import extract_pdf_pages
from .text_processor import metadata_json, preprocess, split_chunks
from .validation import PROTO_RE, clean_text, extract_fields, validate_record


def console_utf8(stream):
    """Reconfigura um fluxo do console para UTF-8, no próprio objeto.

    Sem isso, o console do Windows corrompe os acentos das mensagens
    ("Documento j? processado"), enquanto o arquivo de log sai correto
    (BUG-020). A reconfiguração é feita no lugar de propósito: encapsular o
    fluxo em um TextIOWrapper novo faria o buffer original ser fechado quando
    o invólucro fosse coletado, derrubando a saída do processo.
    """
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
    return stream


def configure_logging(path: Path) -> None:
    """Configura o log em arquivo (UTF-8) e no console, ambos em UTF-8."""
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(path, encoding="utf-8"),
            logging.StreamHandler(console_utf8(sys.stderr)),
        ],
    )


def split_records(page_text: str) -> list[str]:
    """Divide o texto de uma página nos registros individuais de atendimento."""
    parts = re.split(r"(?=Protocolo\s+(?:AT-\d{3}|PROTOCOLO\?))", clean_text(page_text), flags=re.I)
    return [p.strip() for p in parts if re.search(r"Protocolo\s+", p, re.I)]


def process_all(cfg: dict) -> pd.DataFrame:
    """Processa todos os PDFs de entrada e exporta indicadores e gráficos.

    Cada documento é processado em sua própria transação e cada registro em um
    ``SAVEPOINT``: uma falha isolada não descarta o trabalho já concluído
    (BUG-003).

    Args:
        cfg: configuração carregada por :func:`src.config.load_config`.

    Returns:
        O ``DataFrame`` com um registro por atendimento encontrado.
    """
    root = Path(cfg["_root"])
    output = resolve(root, cfg["saida"]["diretorio"])
    output.mkdir(parents=True, exist_ok=True)
    configure_logging(output / cfg["saida"]["log"])
    categorias_path = root / "data" / "auxiliares" / "categorias.json"
    categories = json.loads(categorias_path.read_text(encoding="utf-8"))
    factory = create_session_factory(resolve_sqlite_url(root, cfg["banco"]["url"]))
    pdf_dir = resolve(root, cfg["entrada"]["diretorio_pdfs"])

    # Verifica o OCR uma vez, antes de processar, em vez de descobrir a falha
    # página a página no meio do trabalho (BUG-002).
    ocr_ok, ocr_msg = verificar_ocr(cfg["ocr"].get("tesseract_cmd") or None, cfg["ocr"]["idioma"])
    logging.info("OCR: %s", ocr_msg) if ocr_ok else logging.warning("OCR indisponível — %s", ocr_msg)

    rows: list[dict] = []
    for pdf in sorted(pdf_dir.glob(cfg["entrada"]["padrao"])):
        marca = len(rows)
        try:
            with session_scope(factory) as session:
                _process_document(session, pdf, cfg, categories, rows)
        except Exception as exc:
            # A transação do documento foi revertida: descarta também as linhas
            # que ele havia acrescentado, para que CSV e banco não divirjam.
            del rows[marca:]
            logging.error(
                "Documento descartado por falha na transação: %s (%s: %s)",
                pdf.name,
                type(exc).__name__,
                exc,
            )
            _register_document_failure(factory, pdf, exc)

    df = pd.DataFrame(rows)
    if not df.empty:
        export_results(df, output, cfg["saida"]["csv"], cfg["saida"]["indicadores"])
        generate_charts(df, resolve(root, cfg["saida"]["graficos"]))
    return df


def documentos_sem_registros(cfg: dict) -> list[str]:
    """Lista os documentos que não produziram nenhum atendimento.

    É o sinal que faltava: a entrega perdia um PDF inteiro e ainda assim
    encerrava anunciando sucesso (BUG-002).
    """
    root = Path(cfg["_root"])
    factory = create_session_factory(resolve_sqlite_url(root, cfg["banco"]["url"]))
    with session_scope(factory) as session:
        documentos = session.scalars(select(Documento)).all()
        vazios = []
        for d in documentos:
            tem_atendimento = session.scalar(
                select(Atendimento).where(Atendimento.documento_id == d.id).limit(1)
            )
            # Um documento só de duplicatas não é perda: os registros foram
            # lidos e conscientemente não reinseridos.
            tem_duplicata = session.scalar(
                select(ErroProcessamento)
                .where(ErroProcessamento.documento_id == d.id)
                .where(ErroProcessamento.etapa == "deduplicacao")
                .limit(1)
            )
            if not tem_atendimento and not tem_duplicata:
                vazios.append(d.nome_arquivo)
    return vazios


def _process_document(
    session: Session,
    pdf: Path,
    cfg: dict,
    categories: dict,
    rows: list[dict],
) -> None:
    """Extrai, valida e persiste todos os registros de um documento."""
    digest = sha256(pdf.read_bytes()).hexdigest()
    if session.scalar(select(Documento).where(Documento.hash_sha256 == digest)):
        logging.info("Documento já processado; ignorando: %s", pdf.name)
        return

    page_data = extract_pdf_pages(pdf, cfg["ocr"]["min_caracteres_extracao_direta"])
    doc = Documento(
        nome_arquivo=pdf.name,
        hash_sha256=digest,
        total_paginas=len(page_data),
        metodo="pendente",
    )
    session.add(doc)
    session.flush()

    for page in page_data:
        if page["metodo"] == "ocr_pendente":
            try:
                extraidos = _registros_por_ocr(pdf, page, cfg, categories)
                page["metodo"] = "ocr"
            except Exception as exc:
                session.add(
                    ErroProcessamento(
                        documento_id=doc.id,
                        pagina=page["pagina"],
                        etapa="ocr",
                        tipo=type(exc).__name__,
                        mensagem=str(exc),
                    )
                )
                logging.exception("OCR falhou: %s p.%s", pdf.name, page["pagina"])
                continue
        else:
            extraidos = [
                {"campos": extract_fields(raw), "ilegiveis": set(), "texto": raw}
                for raw in split_records(page["texto"])
            ]
        for registro in extraidos:
            _persist_record(session, doc, pdf, page, registro, cfg, categories, rows)

    # O método do documento reflete o que de fato aconteceu, não a intenção
    # avaliada antes de processar (BUG-022).
    doc.metodo = _metodo_do_documento(page_data)
    session.flush()


def _metodo_do_documento(page_data: list[dict]) -> str:
    """Resume, em uma palavra, como as páginas de um documento foram lidas."""
    metodos = {p["metodo"] for p in page_data}
    if metodos == {"ocr_pendente"}:
        return "falhou"
    processados = metodos - {"ocr_pendente"}
    if len(processados) == 1 and not metodos & {"ocr_pendente"}:
        return processados.pop()
    return "misto"


def _registros_por_ocr(pdf: Path, page: dict, cfg: dict, categories: dict) -> list[dict]:
    """Lê uma página digitalizada célula a célula.

    A extração por texto corrido não funciona nesses documentos: o OCR corrompe
    os próprios rótulos e nenhum padrão casa (BUG-032).
    """
    from .ocr_processor import configurar_tesseract

    configurar_tesseract(cfg["ocr"].get("tesseract_cmd") or None)
    imagem = imagem_da_pagina(pdf, page["pagina"], cfg["ocr"]["dpi"])
    if imagem is None:
        return []
    return extrair_registros(imagem, categories)


def _persist_record(
    session: Session,
    doc: Documento,
    pdf: Path,
    page: dict,
    registro: dict,
    cfg: dict,
    categories: dict,
    rows: list[dict],
) -> None:
    """Valida um registro e o persiste dentro de um ``SAVEPOINT`` próprio.

    Uma falha de integridade afeta apenas este registro: ela é anotada em
    ``erros_processamento`` e o processamento segue para o próximo.
    """
    fields = registro["campos"]
    ilegiveis = registro["ilegiveis"]
    raw = registro["texto"]
    classification, reasons, normalized = validate_record(fields, categories, ilegiveis)
    lido = normalized.get("protocolo") or ""
    # A entrega usava `lido or fallback`: como "PROTOCOLO?" é verdadeiro em
    # contexto booleano, o fallback nunca disparava e dois registros ilegíveis
    # colidiam na mesma chave, virando falsa duplicata (BUG-006).
    if PROTO_RE.fullmatch(lido):
        protocol = lido
    else:
        protocol = "SEM-PROTOCOLO-{0}-{1}-{2}".format(doc.id, page["pagina"], len(rows) + 1)
    if find_by_protocol(session, protocol):
        classification = "duplicado"
        reasons.append("protocolo_duplicado")

    row = {
        **fields,
        "protocolo": protocol,
        "protocolo_bruto": lido,
        "categoria": normalized.get("categoria_normalizada") or fields.get("categoria"),
        "data": normalized.get("data_obj"),
        "tempo_minutos": normalized.get("tempo_obj"),
        "classificacao": classification,
        "motivos": ";".join(reasons),
        "documento": pdf.name,
        "pagina": page["pagina"],
        "metodo": page["metodo"],
    }
    rows.append(row)

    if classification == "duplicado":
        session.add(
            ErroProcessamento(
                documento_id=doc.id,
                pagina=page["pagina"],
                etapa="deduplicacao",
                tipo="Duplicidade",
                mensagem=protocol,
            )
        )
        return

    try:
        with session.begin_nested():
            item = Atendimento(
                documento_id=doc.id,
                pagina=page["pagina"],
                protocolo=protocol,
                data=normalized.get("data_obj"),
                solicitante=fields.get("solicitante"),
                email=fields.get("email"),
                categoria=row["categoria"],
                descricao=fields.get("descricao"),
                solucao=fields.get("solucao"),
                tempo_minutos=normalized.get("tempo_obj"),
                status=fields.get("status"),
                cep=fields.get("cep"),
                municipio=None,
                uf=None,
                classificacao=classification,
                motivos=row["motivos"],
                texto_original=raw,
                texto_limpo=preprocess(raw),
            )
            session.add(item)
            session.flush()
            chunks = split_chunks(
                raw,
                cfg["embeddings"]["tamanho_chunk"],
                cfg["embeddings"]["sobreposicao"],
            )
            for idx, content in enumerate(chunks):
                meta = {
                    "protocolo": protocol,
                    "documento": pdf.name,
                    "pagina": page["pagina"],
                    "categoria": row["categoria"] or "",
                }
                session.add(
                    Chunk(
                        atendimento_id=item.id,
                        documento_id=doc.id,
                        pagina=page["pagina"],
                        indice=idx,
                        conteudo=content,
                        metadata_json=metadata_json(**meta),
                    )
                )
    except (IntegrityError, SQLAlchemyError, ValueError) as exc:
        reasons.append("persistencia_falhou")
        row["motivos"] = ";".join(reasons)
        session.add(
            ErroProcessamento(
                documento_id=doc.id,
                pagina=page["pagina"],
                etapa="persistencia",
                tipo=type(exc).__name__,
                mensagem="{0}: {1}".format(protocol, exc),
            )
        )
        logging.error(
            "Registro %s não persistido (%s); o processamento continua.",
            protocol,
            type(exc).__name__,
        )


def _register_document_failure(factory: sessionmaker, pdf: Path, exc: Exception) -> None:
    """Anota, em transação nova, a falha que reverteu um documento inteiro."""
    try:
        with session_scope(factory) as session:
            session.add(
                ErroProcessamento(
                    documento_id=None,
                    pagina=None,
                    etapa="documento",
                    tipo=type(exc).__name__,
                    mensagem="{0}: {1}".format(pdf.name, exc),
                )
            )
    except Exception:
        logging.exception("Não foi possível registrar a falha do documento %s", pdf.name)
