"""ChromaDB vector store operations"""

import chromadb
from src.config import Config


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=Config.CHROMA_DIR)
        self.collection = self.client.get_or_create_collection(
            name=Config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: list, embeddings: list, metadatas: list):
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def search(self, query_embedding: list, top_k: int = None) -> dict:
        top_k = top_k or Config.TOP_K
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        return results

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        self.client.delete_collection(Config.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=Config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )