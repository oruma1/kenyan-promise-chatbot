"""Retrieval module"""

from src.embeddings import EmbeddingGenerator
from src.vector_store import VectorStore
from src.config import Config


class Retriever:
    def __init__(self):
        self.store = VectorStore()

    def retrieve(self, query: str, top_k: int = None) -> list:
        top_k = top_k or Config.TOP_K
        query_emb = EmbeddingGenerator.embed(query)
        results = self.store.search(query_emb, top_k=top_k)
        retrieved = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                distance = results["distances"][0][i] if "distances" in results else None
                similarity = 1 - distance if distance is not None else 0
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                retrieved.append({
                    "text": doc,
                    "similarity": similarity,
                    "metadata": metadata
                })
        return retrieved

    def has_sufficient_evidence(self, retrieved: list) -> bool:
        return any(r["similarity"] >= Config.SIMILARITY_THRESHOLD for r in retrieved)