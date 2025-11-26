# backend/core/security_user.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
from pathlib import Path
import json
from dotenv import load_dotenv

# carregar .env
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "users.json"

security = HTTPBearer()

# ---------------- UTILIDADES ----------------

def read_users():
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text("utf-8"))
    except:
        return []

# ---------------- DECODIFICAR TOKEN ----------------

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ---------------- PEGAR USUÁRIO LOGADO ----------------

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    token = creds.credentials
    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    users = read_users()
    user = next((u for u in users if u.get("id") == user_id), None)

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user_safe = {k: v for k, v in user.items() if k != "password"}
    return user_safe

# ---------------- SOMENTE ADMIN ----------------

def get_admin_user(user=Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Acesso apenas para administradores.")
    return user
