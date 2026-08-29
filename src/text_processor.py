"""Limpeza linguística e divisão de texto em chunks.

O processamento de linguagem é feito aqui, sem biblioteca externa: uma lista
enxuta de stopwords do português e uma lematização por remoção de sufixos. A
escolha é deliberada — evita exigir o download de um modelo grande — e está
documentada no README, como o RF05 pede.
"""
from __future__ import annotations

import json
import re
import unicodedata

#: Stopwords do português suficientes para o vocabulário destes atendimentos.
STOPWORDS = frozenset({
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "um",
    "uma", "para", "por", "com", "que", "no", "na",
})

#: Sufixos removidos pela lematização leve, do mais longo para o mais curto.
SUFIXOS = ("mente", "coes", "cao", "ando", "endo", "idos", "adas", "ado", "ida", "s")

#: Avanço mínimo por iteração do chunking, em caracteres.
AVANCO_MINIMO = 1


def normalize_text(text: str) -> str:
    """Colapsa espaços e remove caracteres nulos, preservando o conteúdo."""
    return re.sub(r"\s+", " ", text.replace("\x00", " ")).strip()


def tokens(text: str) -> list[str]:
    """Divide o texto em tokens sem acento, minúsculos e sem stopwords."""
    plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return [t for t in re.findall(r"[a-z0-9]+", plain) if t not in STOPWORDS]


def lemma_light(token: str) -> str:
    """Reduz um token à sua raiz aproximada, por remoção de sufixo."""
    for suffix in SUFIXOS:
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            return token[: -len(suffix)]
    return token


def preprocess(text: str) -> str:
    """Devolve a versão limpa do texto, usada na recuperação."""
    return " ".join(lemma_light(t) for t in tokens(text))


def split_chunks(text: str, size: int = 500, overlap: int = 80) -> list[str]:
    """Divide o texto em trechos com sobreposição, cortando em espaço.

    Args:
        text: texto a dividir.
        size: tamanho máximo de cada trecho, em caracteres.
        overlap: sobreposição entre trechos consecutivos.

    Returns:
        Os trechos, sem os vazios.

    Raises:
        ValueError: se ``size`` não for positivo ou se ``overlap`` passar da
            metade de ``size``. A entrega admitia sobreposição até ``size - 1``,
            caso em que o avanço degenerava — 189 trechos para 1.600 caracteres
            com ``size=100, overlap=90`` (BUG-023).
    """
    text = normalize_text(text)
    if size <= 0:
        raise ValueError("O tamanho do chunk precisa ser positivo.")
    if overlap < 0 or overlap > size // 2:
        raise ValueError(
            f"A sobreposição ({overlap}) precisa ficar entre 0 e metade do "
            f"tamanho do chunk ({size // 2})."
        )

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + AVANCO_MINIMO)
    return [c for c in chunks if c]


def metadata_json(**kwargs) -> str:
    """Serializa os metadados de um chunk de forma estável."""
    return json.dumps(kwargs, ensure_ascii=False, sort_keys=True)
