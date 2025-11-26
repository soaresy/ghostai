import json
from pathlib import Path
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

BASE_DIR = Path(__file__).resolve().parent.parent.parent
USERS_FILE = BASE_DIR / "data" / "users.json"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT config (será lido do env no router/main)
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def load_users():
    if not USERS_FILE.exists():
        return []
    return json.loads(USERS_FILE.read_text("utf-8"))

def save_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=2, ensure_ascii=False), "utf-8")

def find_user_by_email(email: str):
    users = load_users()
    for u in users:
        if u.get("email") == email:
            return u
    return None

def create_user(empresa: str, email: str, password: str, role: str = "user"):
    users = load_users()
    if find_user_by_email(email) is not None:
        raise ValueError("Email já cadastrado")
    hashed = get_password_hash(password)
    user = {"empresa": empresa, "email": email, "senha": hashed, "role": role}
    users.append(user)
    save_users(users)
    return user

def create_access_token(data: dict, secret_key: str, algorithm: str, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=60)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return encoded_jwt
