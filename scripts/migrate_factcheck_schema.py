"""Add missing provenance columns to promise_evidence table.

Safe to re-run — checks existing columns before ALTERing.
"""
from src.db import fetch_all, execute


REQUIRED_COLUMNS = {
    "year": "INTEGER",
    "source_url": "TEXT",
    "source_title": "TEXT",
    "verified_by": "TEXT",
    "verified_date": "TEXT",
    "confidence": "TEXT",
}


def main():
    existing = {r["name"] for r in fetch_all("PRAGMA table_info(promise_evidence)")}
    added = []
    for col, typ in REQUIRED_COLUMNS.items():
        if col in existing:
            print(f"[SKIP] {col} already exists")
            continue
        execute(f"ALTER TABLE promise_evidence ADD COLUMN {col} {typ}")
        added.append(col)
        print(f"[OK]   added {col} {typ}")
    print(f"\nDone. {len(added)} new column(s) added.")
    final = sorted(r["name"] for r in fetch_all("PRAGMA table_info(promise_evidence)"))
    print("Final columns:", final)


if __name__ == "__main__":
    main()