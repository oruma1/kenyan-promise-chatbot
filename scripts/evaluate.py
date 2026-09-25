"""Evaluate the RAG system against a BM25 baseline"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retriever import Retriever
from src.evaluator import bm25_baseline, precision_at_k
import pandas as pd


TEST_QUERIES = [
    {"query": "What did they promise about healthcare?", "keywords": ["health", "hospital", "nhif", "medical"]},
    {"query": "What are the education promises?", "keywords": ["education", "school", "learning", "teacher"]},
    {"query": "What about housing?", "keywords": ["housing", "home", "house", "mortgage"]},
    {"query": "What did they promise about jobs?", "keywords": ["jobs", "employment", "youth"]},
    {"query": "What about agriculture?", "keywords": ["farmer", "agriculture", "crop", "fertilizer"]},
]


def main():
    retriever = Retriever()

    all_chunks_raw = retriever.store.collection.get()
    all_chunks = all_chunks_raw["documents"]

    results = []
    for test in TEST_QUERIES:
        rag_results = retriever.retrieve(test["query"], top_k=5)
        rag_precision = precision_at_k(rag_results, test["keywords"], k=5)

        bm25_results = bm25_baseline(test["query"], all_chunks, top_k=5)
        bm25_formatted = [{"text": t} for t, _ in bm25_results]
        bm25_precision = precision_at_k(bm25_formatted, test["keywords"], k=5)

        results.append({
            "Query": test["query"],
            "RAG Precision@5": round(rag_precision, 3),
            "BM25 Precision@5": round(bm25_precision, 3),
            "Delta": round(rag_precision - bm25_precision, 3)
        })

    df = pd.DataFrame(results)
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS: RAG vs BM25 Baseline")
    print("=" * 80)
    print(df.to_string(index=False))
    print(f"\nAverage RAG Precision: {df['RAG Precision@5'].mean():.3f}")
    print(f"Average BM25 Precision: {df['BM25 Precision@5'].mean():.3f}")
    print(f"Average Improvement: {df['Delta'].mean():.3f}")

    df.to_csv("evaluation_results.csv", index=False)
    print("\n[OK] Results saved to evaluation_results.csv")


if __name__ == "__main__":
    main()