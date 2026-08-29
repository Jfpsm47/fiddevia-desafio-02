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
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from .analytics import export_results, generate_charts
from .cep_client import lookup_cep
from .config import resolve, resolve_sqlite_url
from .database import create_session_factory, find_by_protocol, session_scope
from .models import Atendimento, Chunk, Documento, ErroProcessamento
from .ocr_processor import imagem_da_pagina, verificar_ocr
from .ocr_table import extrair_registros, semelhante, separar_municipio_uf
from .pdf_processor import extract_pdf_pages
from .text_processor import metadata_json, preprocess, split_chunks
from .validation import PROTO_RE, clean_text, extract_fields, normalize_key, validate_record


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
    cache_cep: dict[str, tuple[str | None, str | None]] = {}
    vocabulario_municipios: dict[str, str] = {}
    for pdf in sorted(pdf_dir.glob(cfg["entrada"]["padrao"])):
        marca = len(rows)
        try:
            with session_scope(factory) as session:
                _process_document(session, pdf, cfg, categories, rows, cache_cep, vocabulario_municipios)
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
    if df.empty:
        # Nenhum documento novo: o relatório é reconstruído a partir do banco,
        # em vez de deixar CSV, indicadores e gráficos desatualizados sem aviso
        # e anunciar "0 registros" (BUG-014).
        df = _relatorio_do_banco(factory)
        if not df.empty:
            logging.info(
                "Nenhum documento novo. Relatório reconstruído com %s registros já em base.",
                len(df),
            )
    if not df.empty:
        contexto = _contexto_dos_indicadores(factory)
        export_results(df, output, cfg["saida"]["csv"], cfg["saida"]["indicadores"], **contexto)
        generate_charts(df, resolve(root, cfg["saida"]["graficos"]))
    return df


def _contexto_dos_indicadores(factory: sessionmaker) -> dict:
    """Reúne, do banco, os totais que o DataFrame de registros não carrega."""
    with session_scope(factory) as session:
        documentos = session.scalars(select(Documento)).all()
        erros = [
            {"etapa": e.etapa, "tipo": e.tipo}
            for e in session.scalars(select(ErroProcessamento)).all()
        ]
        # Uma página conta uma vez por método, independentemente de quantos
        # registros produziu — o enunciado pede o percentual de páginas. Um
        # documento cujos registros eram todos duplicatas não deixa
        # atendimentos, mas suas páginas foram lidas: por isso a contagem parte
        # do método do documento, e só recorre à leitura por página quando ele
        # é misto.
        paginas_por_metodo: dict[str, int] = {}
        for documento in documentos:
            if documento.metodo != "misto":
                paginas_por_metodo[documento.metodo] = (
                    paginas_por_metodo.get(documento.metodo, 0) + documento.total_paginas
                )
                continue
            vistas = dict(
                session.execute(
                    select(Atendimento.pagina, Atendimento.metodo)
                    .where(Atendimento.documento_id == documento.id)
                    .distinct()
                ).all()
            )
            for metodo in vistas.values():
                paginas_por_metodo[metodo] = paginas_por_metodo.get(metodo, 0) + 1
            restantes = documento.total_paginas - len(vistas)
            if restantes > 0:
                paginas_por_metodo["sem_registro"] = (
                    paginas_por_metodo.get("sem_registro", 0) + restantes
                )
        return {
            "total_documentos": len(documentos),
            "total_paginas": sum(d.total_paginas for d in documentos),
            "paginas_por_metodo": paginas_por_metodo,
            "erros": erros,
        }


def _relatorio_do_banco(factory: sessionmaker) -> pd.DataFrame:
    """Reconstrói o relatório a partir dos registros já persistidos.

    Duplicatas não são reinseridas, por decisão de projeto: elas voltam a
    partir das ocorrências gravadas na etapa de deduplicação.
    """
    with session_scope(factory) as session:
        registros_documento = {d.id: d for d in session.scalars(select(Documento)).all()}
        documentos = {i: d.nome_arquivo for i, d in registros_documento.items()}
        linhas = [
            {
                "protocolo": a.protocolo, "data": a.data, "solicitante": a.solicitante,
                "email": a.email, "categoria": a.categoria, "status": a.status,
                "cep": a.cep, "municipio": a.municipio, "uf": a.uf,
                "tempo_minutos": a.tempo_minutos, "descricao": a.descricao,
                "solucao": a.solucao, "observacoes": a.observacoes,
                "classificacao": a.classificacao, "motivos": a.motivos,
                "documento": documentos.get(a.documento_id), "pagina": a.pagina,
                "metodo": a.metodo,
            }
            for a in session.scalars(select(Atendimento)).all()
        ]
        linhas.extend(
            {
                "protocolo": e.mensagem, "classificacao": "duplicado",
                "motivos": "protocolo_duplicado",
                "documento": documentos.get(e.documento_id), "pagina": e.pagina,
                # A duplicata não é persistida, mas sua página foi lida: o
                # método vem do documento, para o relatório fechar.
                "metodo": getattr(registros_documento.get(e.documento_id), "metodo", None),
            }
            for e in session.scalars(
                select(ErroProcessamento).where(ErroProcessamento.etapa == "deduplicacao")
            ).all()
        )
    return pd.DataFrame(linhas)


def descartar_base(cfg: dict) -> list[str]:
    """Remove banco e coleção vetorial, para um reprocessamento do zero.

    Sem isso, reprocessar exigia apagar ``database/`` à mão: os documentos já
    vistos eram ignorados pelo hash e não havia como recriar a base de forma
    previsível (BUG-014, RF06).

    Returns:
        Os caminhos efetivamente removidos.
    """
    import shutil

    root = Path(cfg["_root"])
    url = resolve_sqlite_url(root, cfg["banco"]["url"])
    removidos = []

    banco = make_url(url).database
    if banco and banco != ":memory:" and Path(banco).exists():
        Path(banco).unlink()
        removidos.append(banco)

    chroma = resolve(root, cfg.get("chromadb", {}).get("diretorio", "database/chroma"))
    if chroma.is_dir():
        shutil.rmtree(chroma)
        removidos.append(str(chroma))
    return removidos


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
    cache_cep: dict,
    vocabulario_municipios: dict,
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
            _persist_record(
                session, doc, pdf, page, registro, cfg, categories, rows,
                cache_cep, vocabulario_municipios,
            )

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


#: Abaixo desta semelhança um município lido por OCR não é associado a nenhum
#: nome conhecido, e passa a ser tratado como ilegível.
CORTE_MUNICIPIO = 0.8


def _registrar_municipio(vocabulario: dict, nome: str | None, autoritativo: bool = False) -> None:
    """Guarda a grafia de um município, preferindo sempre a fonte autoritativa."""
    if not nome:
        return
    chave = normalize_key(nome)
    if autoritativo or chave not in vocabulario:
        vocabulario[chave] = nome


def _canonizar_municipio(vocabulario: dict, nome: str | None, aproximar: bool) -> str | None:
    """Reduz as grafias de um mesmo município a uma só.

    Sem isso, "Cáceres" vindo do ViaCEP e "Caceres" vindo do documento contam
    como cidades diferentes e o indicador por município fica errado.

    Args:
        vocabulario: grafias já conhecidas, por chave sem acento.
        nome: valor lido.
        aproximar: em texto de OCR, admite associar uma grafia degradada
            ("Snop", "Rondonopols") ao nome conhecido mais próximo. Sem
            correspondência, devolve ``None`` — o valor é ilegível, não um
            palpite.
    """
    if not nome:
        return None
    chave = normalize_key(nome)
    if chave in vocabulario:
        return vocabulario[chave]
    if aproximar:
        return semelhante(nome, list(vocabulario.values()), corte=CORTE_MUNICIPIO)
    return nome


def _localidade(cep: str, cfg: dict, cache: dict) -> tuple[str | None, str | None]:
    """Consulta o ViaCEP uma vez por CEP distinto e guarda o resultado.

    Os documentos repetem cerca de nove CEPs em cem registros: sem o cache
    seriam cem requisições para nove respostas. Uma falha de rede, um CEP
    inexistente ou a consulta desligada em ``api.enriquecer_cep`` devolvem
    ``(None, None)`` e nunca interrompem o pipeline (RF07).
    """
    api = cfg.get("api") or {}
    base_url = api.get("cep_base_url")
    if not cep or not base_url or not api.get("enriquecer_cep", True):
        return None, None
    if cep in cache:
        return cache[cep]
    dados = lookup_cep(cep, base_url, api.get("timeout_segundos", 8))
    cache[cep] = (dados["municipio"], dados["uf"]) if dados else (None, None)
    return cache[cep]


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
    cache_cep: dict,
    vocabulario_municipios: dict,
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

    # Município e UF vêm do próprio documento; o ViaCEP tem a palavra final
    # quando o CEP resolve, por ser a fonte autoritativa (RF07).
    municipio, uf = separar_municipio_uf(fields.get("municipio_uf", "")) if fields.get("municipio_uf") else (
        fields.get("municipio", ""), fields.get("uf", "")
    )
    if "municipio" in ilegiveis:
        municipio = ""
    oficial_municipio, oficial_uf = _localidade(normalized.get("cep", ""), cfg, cache_cep)
    _registrar_municipio(vocabulario_municipios, oficial_municipio, autoritativo=True)
    if oficial_municipio:
        municipio = oficial_municipio
    else:
        municipio = _canonizar_municipio(
            vocabulario_municipios, municipio, aproximar=page["metodo"] == "ocr"
        )
        _registrar_municipio(vocabulario_municipios, municipio if page["metodo"] != "ocr" else None)
    if not municipio and page["metodo"] == "ocr":
        reasons.append("municipio_ilegivel")
    uf = (oficial_uf or uf or "").upper()[:2] or None

    row = {
        **fields,
        "protocolo": protocol,
        "protocolo_bruto": lido,
        "municipio": municipio,
        "uf": uf,
        # A categoria oficial pode ser nula: misturá-la ao valor bruto fazia
        # "categoria desconhecida" ser plotada junto das oficiais (BUG-017).
        "categoria": normalized.get("categoria_normalizada"),
        "categoria_bruta": fields.get("categoria"),
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
                metodo=page["metodo"],
                descricao=fields.get("descricao"),
                solucao=fields.get("solucao"),
                tempo_minutos=normalized.get("tempo_obj"),
                status=fields.get("status"),
                cep=fields.get("cep"),
                municipio=municipio,
                uf=uf,
                observacoes=fields.get("observacoes"),
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
                    # Sem a classificação nos metadados não há como impedir que
                    # um registro rejeitado embase uma resposta (BUG-033).
                    "classificacao": classification,
                    "metodo": page["metodo"],
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
