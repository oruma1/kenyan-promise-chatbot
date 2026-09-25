"""Authentication module with role-based access control"""

import hashlib
import json
from pathlib import Path


USERS_FILE = Path(__file__).parent.parent / "data" / "users.json"

# Available roles
ROLES = ["citizen", "evaluator", "admin"]


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _default_users() -> dict:
    """Default accounts for each role"""
    return {
        "admin":     {"password": _hash("admin123"),     "role": "admin"},
        "evaluator": {"password": _hash("evaluator123"), "role": "evaluator"},
        "citizen":   {"password": _hash("citizen123"),   "role": "citizen"},
    }


def _load_users() -> dict:
    if not USERS_FILE.exists():
        USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        users = _default_users()
        USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")
        return users
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return _default_users()


def _save_users(users: dict) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def register_user(username: str, password: str, role: str = "citizen") -> tuple:
    """Register a new user with a role. Returns (success, message)."""
    username = username.strip().lower()
    if not username or not password:
        return False, "Username and password cannot be empty."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if role not in ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(ROLES)}"
    if username in _load_users():
        return False, "Username already exists. Please choose another."

    users = _load_users()
    users[username] = {"password": _hash(password), "role": role}
    _save_users(users)
    return True, f"Account '{username}' created as {role}. You can now log in."


def authenticate(username: str, password: str) -> tuple:
    """Return (success, role) where role is None on failure."""
    username = username.strip().lower()
    users = _load_users()
    if username not in users:
        return False, None
    entry = users[username]
    # Support both old flat format and new nested format
    stored_hash = entry["password"] if isinstance(entry, dict) else entry
    role = entry.get("role", "citizen") if isinstance(entry, dict) else "citizen"
    if stored_hash == _hash(password):
        return True, role
    return False, None


def list_users() -> dict:
    """Return all users with role info (no passwords)."""
    users = _load_users()
    result = {}
    for name, entry in users.items():
        if isinstance(entry, dict):
            result[name] = {"role": entry.get("role", "citizen")}
        else:
            result[name] = {"role": "citizen"}
    return result


def delete_user(username: str) -> tuple:
    """Admin-only: delete a user."""
    username = username.strip().lower()
    if username == "admin":
        return False, "Cannot delete the default admin account."
    users = _load_users()
    if username not in users:
        return False, "User not found."
    del users[username]
    _save_users(users)
    return True, f"User '{username}' deleted."