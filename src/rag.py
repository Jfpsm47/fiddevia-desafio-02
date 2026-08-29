"""Recuperação local e resposta RAG opcional com OpenAI/LangChain."""
from __future__ import annotations

import logging
import os

SYSTEM = (
    "Responda somente com base no contexto. Se a resposta não estiver sustentada, "
    "diga que não há informação suficiente. Cite os protocolos utilizados."
)

#: Abaixo desta similaridade os trechos recuperados não sustentam uma resposta.
LIMIAR_SUFICIENCIA = 0.35

#: Quantos trechos entram na resposta extrativa do modo local.
TRECHOS_NA_RESPOSTA = 3

#: Teto do contexto enviado ao modelo, em caracteres.
LIMITE_CONTEXTO = 6000

SEM_FUNDAMENTO = (
    "Os documentos processados não sustentam uma resposta para esta pergunta. "
    "Os trechos mais próximos ficaram abaixo do limiar de similaridade."
)


def montar_contexto(sources: list[dict], limite: int = LIMITE_CONTEXTO) -> str:
    """Monta o contexto das fontes, respeitando um tamanho máximo (RF13)."""
    partes: list[str] = []
    usado = 0
    for fonte in sources:
        trecho = "[Fonte {} p.{}] {}".format(
            fonte.get("protocolo"), fonte.get("pagina"), fonte.get("conteudo", "")
        )
        if usado + len(trecho) > limite:
            break
        partes.append(trecho)
        usado += len(trecho)
    return "\n\n".join(partes)


def local_answer(question: str, sources: list[dict]) -> dict:
    """Compõe uma resposta extrativa a partir dos trechos recuperados.

    A entrega devolvia sempre o mesmo texto fixo, independentemente do que
    fosse recuperado: sem chave de API o sistema nunca respondia nem declarava
    insuficiência, deixando o RF13 sem demonstração (BUG-034).
    """
    if not sources:
        return {
            "resposta": SEM_FUNDAMENTO,
            "modo": "recuperacao_local",
            "pergunta": question,
            "fontes": [],
            "sustentada": False,
        }

    melhor = max(float(f.get("similaridade") or 0) for f in sources)
    if melhor < LIMIAR_SUFICIENCIA:
        return {
            "resposta": SEM_FUNDAMENTO,
            "modo": "recuperacao_local",
            "pergunta": question,
            "fontes": sources,
            "sustentada": False,
        }

    linhas = [
        "Com base nos atendimentos registrados, os trechos mais próximos da pergunta são:"
    ]
    for fonte in sources[:TRECHOS_NA_RESPOSTA]:
        conteudo = " ".join(str(fonte.get("conteudo", "")).split())
        if len(conteudo) > 400:
            conteudo = conteudo[:400].rsplit(" ", 1)[0] + "…"
        linhas.append(
            "- {} ({}, página {}; similaridade {}): {}".format(
                fonte.get("protocolo"), fonte.get("documento"), fonte.get("pagina"),
                fonte.get("similaridade"), conteudo,
            )
        )
    linhas.append(
        "Resposta montada apenas a partir dos trechos acima. Configure OPENAI_API_KEY "
        "para obter uma síntese em linguagem natural."
    )
    return {
        "resposta": "\n".join(linhas),
        "modo": "recuperacao_local",
        "pergunta": question,
        "fontes": sources,
        "sustentada": True,
    }


def answer(question: str, sources: list[dict], model: str = "gpt-4.1-mini") -> dict:
    """Responde à pergunta, com o modelo quando há chave e localmente quando não.

    Args:
        question: pergunta em linguagem natural.
        sources: trechos recuperados, já ordenados por similaridade.
        model: modelo da OpenAI a usar quando houver chave.

    Returns:
        A resposta, o modo empregado e as fontes citadas.
    """
    if not os.getenv("OPENAI_API_KEY"):
        return local_answer(question, sources)
    if not sources:
        return local_answer(question, sources)
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        prompt = ChatPromptTemplate.from_messages(
            [("system", SYSTEM), ("human", "Pergunta: {question}\n\nContexto:\n{context}")]
        )
        chain = prompt | ChatOpenAI(model=model, temperature=0)
        resposta = chain.invoke({"question": question, "context": montar_contexto(sources)})
        return {
            "resposta": resposta.content,
            "modo": "rag",
            "pergunta": question,
            "fontes": sources,
            "sustentada": True,
        }
    except Exception as exc:
        logging.warning(
            "Falha ao consultar o modelo (%s); caindo para o modo local.", type(exc).__name__
        )
        resultado = local_answer(question, sources)
        resultado["aviso"] = f"Falha no modelo: {type(exc).__name__}"
        return resultado
