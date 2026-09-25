"""Role-based authentication backed by SQLite"""

import hashlib
from typing import Optional, Tuple

from src.db import execute, fetch_one, fetch_all


ROLES = ["citizen", "evaluator", "admin"]


def _hash(password: str) -> str:
    """SHA-256 hash of the password"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# ============================================================
# PUBLIC API
# ============================================================

def register_user(username: str, password: str, role: str = "citizen") -> Tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    username = username.strip().lower()

    if not username or not password:
        return False, "Username and password cannot be empty."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if role not in ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(ROLES)}"

    existing = fetch_one("SELECT user_id FROM users WHERE username = ?", (username,))
    if existing:
        return False, "Username already exists. Please choose another."

    execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        (username, _hash(password), role)
    )
    return True, f"Account '{username}' created as {role}. You can now log in."


def authenticate(username: str, password: str) -> Tuple[bool, Optional[str]]:
    """Return (success, role). role is None on failure."""
    username = username.strip().lower()
    row = fetch_one(
        "SELECT password_hash, role, is_active FROM users WHERE username = ?",
        (username,)
    )
    if not row:
        return False, None
    if not row.get("is_active", 1):
        return False, None
    if row["password_hash"] == _hash(password):
        # Update last_login
        execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
            (username,)
        )
        return True, row["role"]
    return False, None


def list_users() -> dict:
    """Return {username: {role: ...}} for all active users."""
    rows = fetch_all(
        "SELECT username, role, created_at, last_login FROM users ORDER BY username"
    )
    result = {}
    for r in rows:
        result[r["username"]] = {
            "role": r["role"],
            "created_at": r.get("created_at"),
            "last_login": r.get("last_login"),
        }
    return result


def delete_user(username: str) -> Tuple[bool, str]:
    """Delete a user (admin action). Cannot delete 'admin'."""
    username = username.strip().lower()
    if username == "admin":
        return False, "Cannot delete the default admin account."
    row = fetch_one("SELECT user_id FROM users WHERE username = ?", (username,))
    if not row:
        return False, "User not found."
    execute("DELETE FROM users WHERE username = ?", (username,))
    return True, f"User '{username}' deleted."


def get_user_id(username: str) -> Optional[int]:
    """Look up a user's ID by username. Used for logging."""
    row = fetch_one("SELECT user_id FROM users WHERE username = ?", (username.strip().lower(),))
    return row["user_id"] if row else None