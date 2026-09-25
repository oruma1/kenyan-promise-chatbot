"""Evaluation metrics: precision and BM25 baseline"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def bm25_baseline(query: str, chunks: list, top_k: int = 5) -> list:
    if not chunks:
        return []

    vectorizer = TfidfVectorizer(stop_words="english")
    chunk_vecs = vectorizer.fit_transform(chunks)
    query_vec = vectorizer.transform([query])

    scores = cosine_similarity(query_vec, chunk_vecs)[0]
    top_indices = np.argsort(scores)[::-1][:top_k]

    return [(chunks[i], float(scores[i])) for i in top_indices if scores[i] > 0]


def precision_at_k(retrieved: list, relevant_keywords: list, k: int = 5) -> float:
    if not retrieved:
        return 0.0

    relevant_count = 0
    for chunk in retrieved[:k]:
        text = chunk["text"].lower() if isinstance(chunk, dict) else chunk.lower()
        if any(kw.lower() in text for kw in relevant_keywords):
            relevant_count += 1

    return relevant_count / min(k, len(retrieved))