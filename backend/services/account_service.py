# backend/services/account_service.py
from pathlib import Path
import json
from core.security_user import read_users
from backend.routes.auth import hash_password

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "users.json"

def write_users(users):
    DATA_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), "utf-8")

def update_user(user_id: str, updates: dict):
    users = read_users()
    updated = None

    for idx, u in enumerate(users):
        if u.get("id") == user_id:
            users[idx].update(updates)
            updated = users[idx]

    if updated:
        write_users(users)

    return updated

def change_user_password(user_id: str, new_password: str):
    users = read_users()
    for idx, u in enumerate(users):
        if u.get("id") == user_id:
            users[idx]["password"] = hash_password(new_password)
            write_users(users)
            return True
    return False
