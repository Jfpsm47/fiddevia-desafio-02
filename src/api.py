"""API HTTP de consulta."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .config import load_config
from .rag import answer

logger = logging.getLogger(__name__)

cfg = load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carrega modelo e coleção uma vez, na subida do serviço.

    Sem isso cada requisição reconstruía o ``SentenceTransformer`` e reabria o
    ChromaDB, custando 5,5 s por consulta mesmo com o processo aquecido
    (BUG-013). A falha aqui não impede a subida: ``/health`` precisa responder
    para que se possa diagnosticar o problema.
    """
    try:
        from .indexer import preparar

        preparar(cfg)
        logger.info("Modelo de embeddings e coleção vetorial carregados.")
    except Exception:
        logger.exception("Não foi possível preparar a camada de consulta na inicialização.")
    yield


app = FastAPI(title="Atendimentos FIC_DEV", version="1.0.0", lifespan=lifespan)


class AskRequest(BaseModel):
    """Entrada de ``POST /ask``."""

    pergunta: str = Field(min_length=3, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)
    categoria: str | None = None
    incluir_rejeitados: bool = Field(
        default=False,
        description="Admite trechos de registros inválidos ou duplicados como fonte.",
    )


@app.get("/health")
def health() -> dict:
    """Informa se o serviço está de pé e em que modo responderá."""
    return {"status": "ok", "modo": "rag" if os.getenv("OPENAI_API_KEY") else "recuperacao_local"}


@app.post("/ask")
def ask(payload: AskRequest) -> dict:
    """Responde a uma pergunta em linguagem natural, citando as fontes.

    Raises:
        HTTPException: 409 quando a coleção vetorial ainda não foi construída,
            503 quando a camada de consulta está indisponível, 500 no
            inesperado. A entrega convertia tudo em 503 e descartava a causa
            sem registrá-la (BUG-012).
    """
    # Import tardio: mantém /health e a coleta dos testes livres da camada de
    # persistência (BUG-011).
    from .indexer import ColecaoVazia, semantic_query

    try:
        fontes = semantic_query(
            cfg, payload.pergunta, payload.top_k, payload.categoria, payload.incluir_rejeitados
        )
    except ColecaoVazia as exc:
        logger.warning("Consulta sem índice: %s", exc)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ImportError as exc:
        logger.exception("Dependência ausente na camada de consulta.")
        raise HTTPException(
            status_code=503,
            detail=(
                "Camada de consulta indisponível: dependência ausente "
                f"({exc.name}). Execute `pip install -r requirements.txt`."
            ),
        ) from exc
    except Exception as exc:
        logger.exception("Falha inesperada ao recuperar os trechos.")
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao consultar a base ({type(exc).__name__}). Consulte o log do serviço.",
        ) from exc

    return answer(payload.pergunta, fontes, os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
