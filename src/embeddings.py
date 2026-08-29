"""Geração de embeddings e comparação por similaridade de cosseno."""
from __future__ import annotations

import numpy as np


class EmbeddingService:
    """Encapsula o modelo de embeddings local (``sentence-transformers``)."""

    def __init__(self, model_name: str) -> None:
        """Carrega o modelo indicado.

        Args:
            model_name: identificador do modelo no Hugging Face.
        """
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        """Converte textos em vetores normalizados."""
        return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=float)


def cosine_scores(query_vector: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Calcula a similaridade de cosseno entre uma consulta e várias linhas."""
    query = np.asarray(query_vector, dtype=float).reshape(-1)
    data = np.asarray(matrix, dtype=float)
    norma_consulta = np.linalg.norm(query)
    normas = np.linalg.norm(data, axis=1)
    denominador = normas * norma_consulta
    return (data @ query) / np.where(denominador == 0, 1, denominador)


def top_k(
    query: str, texts: list[str], service: EmbeddingService, k: int = 5
) -> list[tuple[int, float]]:
    """Devolve os ``k`` textos mais semelhantes à consulta.

    Args:
        query: pergunta ou trecho de referência.
        texts: candidatos.
        service: serviço de embeddings já carregado.
        k: quantidade de resultados.

    Returns:
        Pares ``(índice, similaridade)``, do mais para o menos semelhante.
    """
    if not texts:
        return []
    vectors = service.encode([query, *texts])
    scores = cosine_scores(vectors[0], vectors[1:])
    return [(int(i), float(scores[i])) for i in np.argsort(scores)[::-1][:k]]
