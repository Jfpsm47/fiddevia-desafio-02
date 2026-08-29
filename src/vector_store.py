"""Persistência e consulta dos chunks no ChromaDB."""
from __future__ import annotations

from pathlib import Path


class ChromaStore:
    """Coleção persistente de chunks, indexada por similaridade de cosseno."""

    def __init__(self, directory: str | Path, collection: str) -> None:
        """Abre ou cria a coleção persistente no diretório informado."""
        import chromadb

        self.client = chromadb.PersistentClient(path=str(directory))
        self.collection = self.client.get_or_create_collection(
            collection, metadata={"hnsw:space": "cosine"}
        )

    def total(self) -> int:
        """Quantos chunks a coleção contém."""
        return int(self.collection.count())

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Insere ou atualiza chunks, sem duplicar os já indexados."""
        self.collection.upsert(
            ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings
        )

    def query(
        self, embedding: list[float], top_k: int = 5, where: dict | None = None
    ) -> list[dict]:
        """Recupera os chunks mais próximos do vetor de consulta.

        Args:
            embedding: vetor da pergunta.
            top_k: quantidade de resultados.
            where: filtro por metadados, no formato do ChromaDB.

        Returns:
            Uma lista com conteúdo, metadados, distância e similaridade.
        """
        result = self.collection.query(query_embeddings=[embedding], n_results=top_k, where=where)
        rows = []
        for i, doc in enumerate((result.get("documents") or [[]])[0]):
            distancia = float(result["distances"][0][i])
            rows.append({
                "conteudo": doc,
                "metadata": result["metadatas"][0][i],
                "distancia": distancia,
                "similaridade": 1 - distancia,
            })
        return rows
