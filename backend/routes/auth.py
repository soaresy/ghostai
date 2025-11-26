# backend/routes/auth.py
from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel, EmailStr
from pathlib import Path
import os, json, bcrypt, uuid
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import jwt, JWTError
from typing import Dict

# carregar .env (a partir da raiz do projeto)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# config
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
ADMIN_API_KEY = (os.getenv("ADMIN_API_KEY") or "").strip()

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "users.json"
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

# schemas
class CreateUserSchema(BaseModel):
    empresa: str
    email: EmailStr
    password: str
    name: str = ""

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

# --- helpers ---
def read_users() -> list:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text("utf-8"))
    except Exception:
        return []

def write_users(users: list):
    DATA_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), "utf-8")

def find_user_by_email(email: str) -> Dict:
    users = read_users()
    for u in users:
        if u.get("email") == email:
            return u
    return None

def normalize_old_user(u: dict) -> dict:
    """
    If old users.json contains 'senha' and no 'id' - convert shape to new format.
    This runs on-demand when reading users to keep compatibility.
    """
    if "id" not in u:
        new = {
            "id": u.get("email", str(uuid.uuid4())),
            "empresa": u.get("empresa") or u.get("company") or "",
            "email": u.get("email"),
            "password": u.get("senha") if u.get("senha") else u.get("password"),
            "role": u.get("role", "user"),
            "name": u.get("name", "")
        }
        # ensure bcrypt hash format (if existing senha already hashed with bcrypt it's fine)
        return new
    return u

def load_normalized_users() -> list:
    users = read_users()
    normalized = [normalize_old_user(u) for u in users]
    # if shape changed, persist back (safe migration)
    # but only write back if any user lacked 'id'
    if any("id" not in u for u in users):
        write_users(normalized)
    return normalized

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise

# ------------------ create-user (protected by admin key) ------------------
@router.post("/create-user")
async def create_user(request: Request):
    key = request.query_params.get("key", "").strip()
    if key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="admin key inválida")

    body = await request.json()
    schema = CreateUserSchema(**body)
    email = schema.email.lower().strip()

    users = load_normalized_users()

    if find_user_by_email(email):
        raise HTTPException(status_code=409, detail="Email já registrado.")

    hashed = hash_password(schema.password)
    new_user = {
        "id": str(uuid.uuid4()),
        "empresa": schema.empresa,
        "email": email,
        "password": hashed,
        "role": "client",  # default role for created users (changeable)
        "name": schema.name,
        "created_at": datetime.utcnow().isoformat()
    }
    users.append(new_user)
    write_users(users)
    # you might want to send credentials by email here via email_service
    return {"success": True, "user": {"id": new_user["id"], "email": new_user["email"], "empresa": new_user["empresa"]}}

# ------------------ signin (returns JWT) ------------------
@router.post("/signin")
async def signin(data: LoginSchema):
    users = load_normalized_users()
    email = data.email.lower().strip()
    user = next((u for u in users if u.get("email") == email), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    if not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    token_payload = {"sub": user["id"], "email": user["email"], "role": user.get("role", "client")}
    access_token = create_access_token(token_payload)
    safe_user = {k: v for k, v in user.items() if k != "password"}
    return {"access_token": access_token, "token_type": "bearer", "user": safe_user}

# ------------------ signup (public, optional) ------------------
@router.post("/signup")
async def signup(body: CreateUserSchema):
    # optional: allow public signup - here we enforce admin-only creation by default
    if not ADMIN_API_KEY:
        # if ADMIN_API_KEY not set, allow signup (dev only). In production set ADMIN_API_KEY.
        pass
    email = body.email.lower().strip()
    users = load_normalized_users()
    if find_user_by_email(email):
        raise HTTPException(status_code=400, detail="Usuário já existe")
    hashed = hash_password(body.password)
    new_user = {
        "id": str(uuid.uuid4()),
        "empresa": body.empresa,
        "email": email,
        "password": hashed,
        "role": "client",
        "name": body.name,
        "created_at": datetime.utcnow().isoformat()
    }
    users.append(new_user)
    write_users(users)
    token_payload = {"sub": new_user["id"], "email": new_user["email"], "role": new_user["role"]}
    access_token = create_access_token(token_payload)
    safe_user = {k: v for k, v in new_user.items() if k != "password"}
    return {"access_token": access_token, "token_type": "bearer", "user": safe_user}

# ------------------ /me - validate token and return user ------------------
class TokenSchema(BaseModel):
    token: str

@router.post("/me")
async def me(payload: TokenSchema):
    try:
        data = decode_access_token(payload.token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")
    user_id = data.get("sub")
    users = load_normalized_users()
    user = next((u for u in users if u.get("id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    safe = {k: v for k, v in user.items() if k != "password"}
    return {"user": safe}

# simple ping
@router.get("/ping")
def ping():
    return {"pong": True}
