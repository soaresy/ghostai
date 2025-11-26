# backend/main.py
import os
import json
import logging
from pathlib import Path
from io import BytesIO
from datetime import timedelta

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from dotenv import load_dotenv
from jose import JWTError, jwt

# --- carregar .env (usa .env da raiz do projeto) ---
HERE = Path(__file__).resolve().parents[1]
ENV_PATH = HERE.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# --- logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghostai")

# --- fastapi app ---
app = FastAPI(title="IA-FANTASMA Backend (modular)")

# --- config / paths ---
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ONBOARDING_FILE = DATA_DIR / "onboarding.json"

# env vars
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", SMTP_USER or "")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")

SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# --- CORS (ajuste em produção) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # mudar para seu domínio em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- static mounts (frontend) ---
app.mount("/landing-static", StaticFiles(directory=FRONTEND_DIR / "landing" / "static"), name="landing-static")
app.mount("/landing-js", StaticFiles(directory=FRONTEND_DIR / "landing" / "js"), name="landing-js")
app.mount("/dashboard-static", StaticFiles(directory=FRONTEND_DIR / "dashboard"), name="dashboard-static")
app.mount("/login-static", StaticFiles(directory=FRONTEND_DIR / "login"), name="login-static")
# expose uploads if you save there
UPLOADS_DIR = FRONTEND_DIR / "dashboard" / "assets" / "user_uploads"
if UPLOADS_DIR.exists():
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

# --- templates (dashboard dynamic) ---
templates = Jinja2Templates(directory=str(HERE / "templates"))

# --- include routers if exist (graceful) ---
try:
    from backend.routes import auth as auth_module
    app.include_router(auth_module.router)
except Exception as e:
    logger.warning("Router auth not included: %s", e)

for module_name in ("account", "client", "admin", "dashboard"):
    try:
        mod = __import__(f"backend.routes.{module_name}", fromlist=["router"])
        app.include_router(mod.router)
    except Exception:
        # not fatal; we may not have some modules yet
        pass

# ---------------------------
# Utils: token extraction from cookie
# ---------------------------
def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# ---------------------------
# Onboarding storage / pdf / email (kept compatible com sua versão)
# ---------------------------
def save_data(data: dict):
    ONBOARDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(ONBOARDING_FILE.read_text("utf-8")) if ONBOARDING_FILE.exists() else []
    except Exception:
        existing = []
    existing.append(data)
    ONBOARDING_FILE.write_text(json.dumps(existing, indent=4, ensure_ascii=False), "utf-8")

def generate_pdf(data: dict) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    x, y = 40, 800

    def section(title):
        nonlocal y
        c.setFont("Helvetica-Bold", 14)
        c.drawString(x, y, title)
        y -= 20
        c.setLineWidth(1)
        c.line(x, y, x + 500, y)
        y -= 20

    def line(label, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, f"{label}:")
        c.setFont("Helvetica", 10)
        c.drawString(x + 140, y, str(value or "-"))
        y -= 18

    def block(label, text):
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, f"{label}:")
        y -= 16
        c.setFont("Helvetica", 10)
        if not text: text = "-"
        paragraphs = [text[i:i+90] for i in range(0, len(text), 90)]
        for p in paragraphs:
            c.drawString(x + 10, y, p)
            y -= 14
        y -= 10

    section("Informações Básicas")
    line("Nome", data.get("nome"))
    line("Email", data.get("email"))
    line("WhatsApp", data.get("whatsapp"))
    line("Empresa", data.get("empresa"))

    section("Diagnóstico")
    line("Segmento", data.get("segmento"))
    line("Volume diário", data.get("volume"))
    line("Canais", ", ".join(data.get("canal", [])))
    line("Objetivos", ", ".join(data.get("objetivo", [])))

    section("Descrição Geral")
    block("Resumo do negócio", data.get("descricao", "Não informado"))

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, 40, "Gerado automaticamente pelo GhostAI 👻")
    c.save()
    return buffer.getvalue()

def send_email_with_pdf(data: dict):
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("Envio de e-mail desativado (credenciais não configuradas).")
        return

    pdf_bytes = generate_pdf(data)

    html_body = f"""
    <!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"></head><body>
    <h2>Novo Lead Recebido</h2>
    <p>Nome: {data.get('nome','-')}</p>
    <p>Email: {data.get('email','-')}</p>
    <p>WhatsApp: {data.get('whatsapp','-')}</p>
    <p>Empresa: {data.get('empresa','-')}</p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_USER
    msg["To"] = ADMIN_EMAIL
    msg["Subject"] = "Novo Lead - GhostAI"
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    pdf_attachment.add_header("Content-Disposition", "attachment", filename="lead_ghostai.pdf")
    msg.attach(pdf_attachment)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, ADMIN_EMAIL, msg.as_string())
        logger.info("Email enviado com sucesso para %s", ADMIN_EMAIL)
    except Exception as e:
        logger.exception("Erro ao enviar email: %s", e)

# ---------------------------
# Routes: landing + onboarding + chat (compatíveis)
# ---------------------------
@app.get("/", response_class=FileResponse)
def home():
    return FileResponse(FRONTEND_DIR / "landing" / "index.html")

@app.get("/checkout", response_class=FileResponse)
def checkout():
    return FileResponse(FRONTEND_DIR / "landing" / "checkout.html")

@app.get("/onboarding", response_class=FileResponse)
def onboarding_page():
    return FileResponse(FRONTEND_DIR / "landing" / "onboarding.html")

@app.get("/success", response_class=FileResponse)
def success_page():
    return FileResponse(FRONTEND_DIR / "landing" / "success.html")

@app.get("/login", response_class=FileResponse)
def login_page():
    return FileResponse(FRONTEND_DIR / "login" / "index.html")

@app.get("/dashboard", response_class=FileResponse)
def dashboard_page(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    # serve single dashboard entry (frontend fetchará dados via API)
    return FileResponse(FRONTEND_DIR / "dashboard" / "index.html")

@app.post("/api/onboarding")
async def receive_form(request: Request):
    data = await request.json()
    save_data(data)
    # send email async would be better; here synchronous for compatibility
    try:
        send_email_with_pdf(data)
    except Exception:
        logger.exception("Erro no envio de email (onboarding)")
    return {"success": True, "redirect": "/success"}

@app.post("/api/chat")
async def api_chat(req: Request):
    payload = await req.json()
    msg = payload.get("message")
    history = payload.get("history", [])
    if not msg:
        raise HTTPException(status_code=400, detail="Mensagem é obrigatória")
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "messages": history + [{"role": "user", "content": msg}]},
            timeout=8
        )
        reply = r.json().get("message", {}).get("content", "")
        return {"reply": reply}
    except Exception:
        logger.exception("Erro ao consultar Ollama")
        return {"reply": "IA indisponível no momento."}

# health
@app.get("/health")
def health():
    return {"status": "ok"}

# ---------------------------
# start hint for uvicorn
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
