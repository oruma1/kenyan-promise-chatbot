"""Initialize the SQLite database for the RAG chatbot"""

import sqlite3
import sys
import os
import hashlib
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import Config


DB_PATH = Path(Config.DATA_DIR).parent / "chatbot.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_database():
    print("=" * 60)
    print("Initializing database")
    print("=" * 60)
    print(f"Database: {DB_PATH}")

    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Read schema
    if not SCHEMA_PATH.exists():
        print(f"[ERROR] Schema file not found: {SCHEMA_PATH}")
        return

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    # Create tables
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema)
    conn.commit()

    # Seed default users
    cursor = conn.cursor()
    defaults = [
        ("admin",     _hash("admin123"),     "admin"),
        ("evaluator", _hash("evaluator123"), "evaluator"),
        ("citizen",   _hash("citizen123"),   "citizen"),
    ]
    for u, p, r in defaults:
        cursor.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (u, p, r)
        )
    conn.commit()

    # Verify
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    print(f"\nCreated {len(tables)} tables:")
    for (t,) in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  [OK] {t:20s}  {count} rows")

    users = cursor.execute("SELECT username, role FROM users").fetchall()
    print(f"\nSeeded users:")
    for u, r in users:
        print(f"  - {u:12s} ({r})")

    conn.close()
    print("\n[OK] Database initialized successfully.")
    print(f"  File: {DB_PATH}")


if __name__ == "__main__":
    init_database()