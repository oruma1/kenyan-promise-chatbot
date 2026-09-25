"""SQLite database wrapper for the Kenyan RAG Chatbot"""

import sqlite3
from pathlib import Path
from typing import Optional

from src.config import Config


DB_PATH = Path(Config.DATA_DIR).parent / "chatbot.db"


def _connect() -> sqlite3.Connection:
    """Open a connection with row factory and FK enforcement"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def execute(query: str, params: tuple = ()) -> int:
    """Run an INSERT/UPDATE/DELETE. Returns lastrowid."""
    conn = _connect()
    try:
        cur = conn.execute(query, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def execute_many(query: str, params_list: list) -> None:
    """Run a batch of INSERTs"""
    conn = _connect()
    try:
        conn.executemany(query, params_list)
        conn.commit()
    finally:
        conn.close()


def fetch_one(query: str, params: tuple = ()) -> Optional[dict]:
    """Return a single row as dict, or None"""
    conn = _connect()
    try:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def fetch_all(query: str, params: tuple = ()) -> list:
    """Return all rows as list of dicts"""
    conn = _connect()
    try:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def table_exists(name: str) -> bool:
    """Check if a table exists (useful for startup checks)"""
    row = fetch_one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,)
    )
    return row is not None