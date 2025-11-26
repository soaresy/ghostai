from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pathlib import Path
import json, os, bcrypt
from dotenv import load_dotenv

# Garantir carregamento do .env a partir da raiz do projeto
from pathlib import Path
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Carregar chave admin
ADMIN_API_KEY = (os.getenv("ADMIN_API_KEY") or "").strip()

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "users.json"


class CreateUser(BaseModel):
    empresa: str
    email: str
    password: str


# ------------------ CRIAR USUÁRIO (PROTEGIDO POR ADMIN_API_KEY) ------------------
@router.post("/create-user")
async def create_user(request: Request):
    # Ler query param
    key = request.query_params.get("key", "").strip()

    if key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="admin key inválida")

    body = await request.json()

    empresa = body.get("empresa", "").strip()
    email = body.get("email", "").lower().strip()
    password = body.get("password", "").strip()

    if not empresa or not email or not password:
        raise HTTPException(status_code=400, detail="Dados faltando.")

    # Gerar hash da senha
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    # Carregar lista de usuários
    users = []
    if DATA_FILE.exists():
        users = json.loads(DATA_FILE.read_text("utf-8"))

    # Verificar duplicidade
    for u in users:
        if u["email"] == email:
            raise HTTPException(status_code=409, detail="Email já registrado.")

    # Criar usuário novo
    user = {
        "empresa": empresa,
        "email": email,
        "senha": hashed,
        "role": "user"
    }

    users.append(user)
    DATA_FILE.write_text(json.dumps(users, indent=4, ensure_ascii=False), "utf-8")

    return {"success": True, "user": user}


# ------------------ LOGIN ------------------
class LoginData(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(data: LoginData):
    users = []
    if DATA_FILE.exists():
        users = json.loads(DATA_FILE.read_text("utf-8"))

    user = next((u for u in users if u["email"] == data.email.lower().strip()), None)

    if not user:
        raise HTTPException(status_code=401, detail="Email não encontrado")

    if not bcrypt.checkpw(data.password.encode(), user["senha"].encode()):
        raise HTTPException(status_code=401, detail="Senha incorreta")

    return {"success": True, "email": user["email"], "empresa": user["empresa"]}
