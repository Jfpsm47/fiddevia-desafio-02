"""Indexação dos chunks persistidos e consulta semântica."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .config import resolve_sqlite_url
from .embeddings import EmbeddingService
from .models import Chunk
from .vector_store import ChromaStore

#: Classificações cujos trechos não devem embasar uma resposta por padrão. Um
#: registro que o próprio sistema rejeitou não é fonte confiável (BUG-033).
CLASSIFICACOES_CONFIAVEIS = ("valido", "incompleto")


class ColecaoVazia(RuntimeError):
    """A coleção vetorial não existe ou não tem chunks indexados."""


@lru_cache(maxsize=4)
def _servico(modelo: str) -> EmbeddingService:
    """Carrega o modelo de embeddings uma única vez por processo.

    A entrega construía um ``SentenceTransformer`` a cada consulta, o que
    custava 5,5 s por requisição mesmo com o processo aquecido (BUG-013).
    """
    logging.info("Carregando modelo de embeddings: %s", modelo)
    return EmbeddingService(modelo)


@lru_cache(maxsize=4)
def _colecao(diretorio: str, nome: str) -> ChromaStore:
    """Abre a coleção do ChromaDB uma única vez por processo."""
    return ChromaStore(diretorio, nome)


def preparar(cfg: dict) -> None:
    """Aquece modelo e coleção, para que a primeira consulta não pague por eles."""
    root = Path(cfg["_root"])
    _servico(cfg["embeddings"]["modelo"])
    _colecao(str(root / cfg["chromadb"]["diretorio"]), cfg["chromadb"]["colecao"])


def build_index(cfg: dict) -> int:
    """Gera os embeddings dos chunks persistidos e os grava no ChromaDB.

    Returns:
        A quantidade de chunks indexados.
    """
    root = Path(cfg["_root"])
    url = resolve_sqlite_url(root, cfg["banco"]["url"])
    with Session(create_engine(url)) as session:
        chunks = list(session.scalars(select(Chunk)).all())
    if not chunks:
        return 0

    service = _servico(cfg["embeddings"]["modelo"])
    documentos = [c.conteudo for c in chunks]
    vetores = service.encode(documentos)
    store = _colecao(str(root / cfg["chromadb"]["diretorio"]), cfg["chromadb"]["colecao"])
    store.upsert(
        [str(c.id) for c in chunks],
        documentos,
        [json.loads(c.metadata_json) for c in chunks],
        vetores.tolist(),
    )
    return len(chunks)


def semantic_query(
    cfg: dict,
    question: str,
    top_k: int = 5,
    category: str | None = None,
    incluir_rejeitados: bool = False,
) -> list[dict]:
    """Recupera os trechos mais semelhantes à pergunta.

    Args:
        cfg: configuração carregada.
        question: pergunta em linguagem natural.
        top_k: quantidade de trechos desejada.
        category: restringe a uma categoria oficial.
        incluir_rejeitados: admite trechos de registros inválidos ou
            duplicados, que ficam de fora por padrão.

    Returns:
        Os trechos, com procedência e pontuação de similaridade.

    Raises:
        ColecaoVazia: quando não há nada indexado.
    """
    root = Path(cfg["_root"])
    service = _servico(cfg["embeddings"]["modelo"])
    store = _colecao(str(root / cfg["chromadb"]["diretorio"]), cfg["chromadb"]["colecao"])
    if not store.total():
        raise ColecaoVazia(
            "Nenhum chunk indexado. Execute `python -m src.main --indexar` antes de consultar."
        )

    filtros = []
    if category:
        filtros.append({"categoria": category})
    if not incluir_rejeitados:
        filtros.append({"classificacao": {"$in": list(CLASSIFICACOES_CONFIAVEIS)}})
    where = filtros[0] if len(filtros) == 1 else ({"$and": filtros} if filtros else None)

    consulta = service.encode([question])[0].tolist()
    linhas = store.query(consulta, top_k, where)
    return [
        {**linha["metadata"], "conteudo": linha["conteudo"],
         "similaridade": round(linha["similaridade"], 4)}
        for linha in linhas
    ]
