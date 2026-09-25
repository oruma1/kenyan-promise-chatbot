"""Script to ingest all documents in data/documents/"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.document_loader import load_all_documents
from src.promise_filter import PromiseFilter, chunk_text
from src.embeddings import EmbeddingGenerator
from src.vector_store import VectorStore
from src.config import Config


def main():
    print("=" * 60)
    print("RAG Chatbot - Document Ingestion")
    print("=" * 60)

    print(f"\n[1/4] Loading documents from {Config.DATA_DIR}...")
    documents = load_all_documents(Config.DATA_DIR)
    if not documents:
        print("No documents found. Add PDFs or TXTs to data/documents/")
        return
    print(f"Loaded {len(documents)} documents")

    print("\n[2/4] Chunking and filtering for promises...")
    filter_module = PromiseFilter()
    all_chunks = []
    all_metadata = []

    for doc in documents:
        chunks = chunk_text(doc["text"])
        promise_count = 0
        for i, chunk in enumerate(chunks):
            is_promise, score, matched = filter_module.is_promise(chunk)
            if is_promise:
                all_chunks.append(chunk)
                all_metadata.append({
                    "document_id": doc["document_id"],
                    "title": doc["title"],
                    "year": doc["year"],
                    "party": doc["party"],
                    "source_type": doc["source_type"],
                    "promise_score": score,
                    "chunk_index": i
                })
                promise_count += 1
        print(f"  {doc['title']}: {promise_count}/{len(chunks)} promise chunks")

    if not all_chunks:
        print("No promise chunks found.")
        return

    print(f"\nTotal promise chunks: {len(all_chunks)}")

    print("\n[3/4] Generating embeddings...")
    embeddings = EmbeddingGenerator.embed(all_chunks)
    print(f"Generated {len(embeddings)} embeddings")

    print("\n[4/4] Storing in ChromaDB...")
    store = VectorStore()
    store.reset()
    store.add_chunks(all_chunks, embeddings, all_metadata)
    print(f"[OK] Stored {store.count()} chunks in vector database")

    print("\n" + "=" * 60)
    print("Ingestion complete! Run: streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()