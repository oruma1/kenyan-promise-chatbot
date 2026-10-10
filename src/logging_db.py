"""Database logging helpers for queries, responses, citations, feedback, evaluations"""

from typing import Optional, List, Dict
from src.db import execute, fetch_one, fetch_all


# ============================================================
# QUERIES
# ============================================================

def log_query(user_id: int, query_text: str) -> int:
    """Insert a query and return its query_id."""
    return execute(
        "INSERT INTO queries (user_id, query_text) VALUES (?, ?)",
        (user_id, query_text)
    )


def mark_query_answered(query_id: int) -> None:
    """Mark a query as answered."""
    execute("UPDATE queries SET was_answered = 1 WHERE query_id = ?", (query_id,))


# ============================================================
# RESPONSES
# ============================================================

def log_response(
    query_id: int,
    response_text: str,
    retrieval_ms: int = 0,
    generation_ms: int = 0,
    model_version: str = "llama3:8b"
) -> int:
    """Insert a response and return its response_id."""
    return execute(
        """INSERT INTO responses
           (query_id, response_text, retrieval_ms, generation_ms, model_version)
           VALUES (?, ?, ?, ?, ?)""",
        (query_id, response_text, retrieval_ms, generation_ms, model_version)
    )


# ============================================================
# CITATIONS
# ============================================================

def log_citations(response_id: int, retrieved_chunks: List[Dict]) -> None:
    """Bulk-insert citations for a response."""
    if not retrieved_chunks:
        return
    rows = []
    for i, chunk in enumerate(retrieved_chunks):
        chunk_id = chunk.get("metadata", {}).get("chunk_id")
        if chunk_id is None:
            continue
        rows.append((
            response_id,
            chunk_id,
            i + 1,
            float(chunk.get("similarity", 0.0))
        ))
    if rows:
        execute_many(
            """INSERT INTO citations
               (response_id, chunk_id, citation_order, similarity)
               VALUES (?, ?, ?, ?)""",
            rows
        )


# ============================================================
# FEEDBACK
# ============================================================

def log_feedback(
    response_id: int,
    user_id: int,
    feedback_type: str,
    comment: Optional[str] = None
) -> int:
    """Insert feedback. feedback_type must be 'positive' or 'negative'."""
    if feedback_type not in ("positive", "negative"):
        raise ValueError("feedback_type must be 'positive' or 'negative'")
    return execute(
        """INSERT INTO feedback (response_id, user_id, feedback_type, comment)
           VALUES (?, ?, ?, ?)""",
        (response_id, user_id, feedback_type, comment)
    )


# ============================================================
# EVALUATIONS
# ============================================================

def log_evaluation(
    evaluator_id: int,
    test_query: str,
    precision_at_5: float,
    bm25_precision: float,
    faithfulness: Optional[float] = None
) -> int:
    """Insert an automated evaluation and return its eval_id."""
    return execute(
        """INSERT INTO evaluations
           (evaluator_id, test_query, precision_at_5, bm25_precision, faithfulness)
           VALUES (?, ?, ?, ?, ?)""",
        (evaluator_id, test_query, precision_at_5, bm25_precision, faithfulness)
    )


# ============================================================
# HUMAN REVIEWS
# ============================================================

def log_human_review(
    reviewer_id: int,
    query_text: str,
    answer_text: str,
    accuracy_score: int,
    relevance_score: int,
    citation_score: int,
    comments: Optional[str] = None,
    eval_id: Optional[int] = None
) -> int:
    """Insert a human review and return its review_id."""
    return execute(
        """INSERT INTO human_reviews
           (eval_id, reviewer_id, query_text, answer_text,
            accuracy_score, relevance_score, citation_score, comments)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (eval_id, reviewer_id, query_text, answer_text,
         accuracy_score, relevance_score, citation_score, comments)
    )


# ============================================================
# VIEW / HISTORY
# ============================================================

def get_recent_queries(user_id: int, limit: int = 20) -> List[Dict]:
    """Return the last N queries for a user with response text."""
    return fetch_all(
        """SELECT q.query_id, q.query_text, q.timestamp, q.was_answered,
                  r.response_text, r.retrieval_ms, r.generation_ms
           FROM queries q
           LEFT JOIN responses r ON r.query_id = q.query_id
           WHERE q.user_id = ?
           ORDER BY q.timestamp DESC
           LIMIT ?""",
        (user_id, limit)
    )


def get_feedback_stats() -> Dict:
    """Return aggregate feedback counts (admin view)."""
    row = fetch_one(
        """SELECT
             SUM(CASE WHEN feedback_type = 'positive' THEN 1 ELSE 0 END) AS positives,
             SUM(CASE WHEN feedback_type = 'negative' THEN 1 ELSE 0 END) AS negatives,
             COUNT(*) AS total
           FROM feedback"""
    ) or {}
    return {
        "positives": int(row.get("positives") or 0),
        "negatives": int(row.get("negatives") or 0),
        "total": int(row.get("total") or 0)
    }


def get_recent_evaluations(limit: int = 20) -> List[Dict]:
    """Return recent automated evaluations."""
    return fetch_all(
        """SELECT e.*, u.username AS evaluator
           FROM evaluations e
           LEFT JOIN users u ON u.user_id = e.evaluator_id
           ORDER BY e.run_at DESC
           LIMIT ?""",
        (limit,)
    )


def get_recent_reviews(limit: int = 20) -> List[Dict]:
    """Return recent human reviews."""
    return fetch_all(
        """SELECT h.*, u.username AS reviewer
           FROM human_reviews h
           LEFT JOIN users u ON u.user_id = h.reviewer_id
           ORDER BY h.created_at DESC
           LIMIT ?""",
        (limit,)
    )