from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from jose import jwt, JWTError
from pathlib import Path
import json, os, smtplib, logging, requests

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# imports adicionais
from dotenv import load_dotenv
from pathlib import Path
import os
from backend.routes.dashboard import router as dashboard_router
from backend.routes.auth import router as auth_router

# carregar .env
ENV_PATH = Path("C:/Users/soare/ia-fantasma/.env")

load_dotenv(dotenv_path=ENV_PATH)
print("Carregando .env de:", ENV_PATH)

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ghostai")

# =====================================================================
# 📌 INSTÂNCIA FASTAPI — *DEVE EXISTIR APENAS 1*
# =====================================================================
app = FastAPI()

# =====================================================================
# 📌 DIRETÓRIOS DO PROJETO (CORRETOS PARA A SUA ESTRUTURA)
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "onboarding.json"

# =====================================================================
# 📌 VARIÁVEIS DE AMBIENTE
# =====================================================================
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", SMTP_USER or "")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")

SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# =====================================================================
# 📌 MIDDLEWARES
# =====================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# 📌 STATIC FILES
# =====================================================================
app.mount("/landing-static",
          StaticFiles(directory=FRONTEND_DIR / "landing" / "static"),
          name="landing-static")

app.mount("/landing-js",
          StaticFiles(directory=FRONTEND_DIR / "landing" / "js"),
          name="landing-js")

app.mount("/dashboard-static",
          StaticFiles(directory=FRONTEND_DIR / "dashboard"),
          name="dashboard-static")

app.mount("/login-static",
          StaticFiles(directory=FRONTEND_DIR / "login"),
          name="login-static")

# =====================================================================
# 📌 REGISTRAR ROUTERS (AUTH + DASHBOARD)
# =====================================================================
app.include_router(auth_router)
app.include_router(dashboard_router)

# =====================================================================
# 📌 FUNÇÃO — VALIDAR TOKEN JWT A PARTIR DO COOKIE
# =====================================================================
def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# =====================================================================
# 📌 ROTAS DO SITE (LANDING)
# =====================================================================
@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "landing" / "index.html")

@app.get("/checkout")
def checkout():
    return FileResponse(FRONTEND_DIR / "landing" / "checkout.html")

@app.get("/onboarding")
def onboarding():
    return FileResponse(FRONTEND_DIR / "landing" / "onboarding.html")

@app.get("/success")
def success():
    return FileResponse(FRONTEND_DIR / "landing" / "success.html")

# =====================================================================
# 📌 ROTA - LOGIN (NÃO PROTEGIDA)
# =====================================================================
@app.get("/login")
def login():
    return FileResponse(FRONTEND_DIR / "login" / "index.html")

# =====================================================================
# 📌 ROTA - DASHBOARD PROTEGIDA (JWT)
# =====================================================================
@app.get("/dashboard")
def dashboard(request: Request):
    user = get_current_user_from_cookie(request)
    if not user:
        return RedirectResponse("/login")
    return FileResponse(FRONTEND_DIR / "dashboard" / "index.html")

# =====================================================================
# 📌 SALVAR FORMULÁRIO
# =====================================================================
def save_data(data: dict):
    DATA_DIR.mkdir(exist_ok=True)
    try:
        existing = json.loads(DATA_FILE.read_text("utf-8")) if DATA_FILE.exists() else []
    except:
        existing = []
    existing.append(data)
    DATA_FILE.write_text(json.dumps(existing, indent=4, ensure_ascii=False), "utf-8")

# =====================================================================
# 📌 GERAR PDF
# =====================================================================
def generate_pdf(data: dict) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    x = 40
    y = 800

    # Título
    c.setFont("Helvetica-Bold", 20)
    c.drawString(x, y, "📄 Lead — GhostAI")
    y -= 40

    # ---- Helpers ----
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

        if not text:
            text = "-"

        # quebra automática
        paragraphs = [text[i:i+90] for i in range(0, len(text), 90)]
        for p in paragraphs:
            c.drawString(x + 10, y, p)
            y -= 14
        y -= 10

    # ---- SEÇÕES ----
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
    descricao = data.get("descricao", "Não informado")
    block("Resumo do negócio", descricao)

    # Rodapé
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, 40, "Gerado automaticamente pelo GhostAI 👻")

    c.save()
    return buffer.getvalue()

# =====================================================================
# 📌 ENVIAR EMAIL
# =====================================================================
def send_email(data: dict):
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("Envio de e-mail desativado.")
        return

    pdf_bytes = generate_pdf(data)

    # ------------------ EMAIL HTML PREMIUM ------------------
    html_body = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Novo Lead - GhostAI</title>
      <style>
        body {{
          background: #f6f6f9;
          font-family: Arial, sans-serif;
          margin: 0; padding: 20px;
          color: #333;
        }}
        .container {{
          max-width: 620px;
          margin: auto;
          background: #fff;
          border-radius: 14px;
          padding: 25px 30px;
          box-shadow: 0 6px 25px rgba(0,0,0,0.08);
        }}
        h2 {{
          margin-top: 0;
        }}
        .section-title {{
          font-weight: bold;
          color: #444;
          font-size: 15px;
          margin-top: 25px;
          border-left: 4px solid #6C63FF;
          padding-left: 8px;
        }}
        .box {{
          background: #f2f2f7;
          padding: 12px 15px;
          border-radius: 8px;
          margin-top: 8px;
        }}
        .label {{
          font-weight: bold;
          color: #555;
        }}
        .footer {{
          text-align: center;
          font-size: 13px;
          color: #777;
          margin-top: 30px;
        }}
      </style>
    </head>
    <body>

    <div class="container">
      <h2>🚀 Novo Lead Recebido</h2>

      <p>Aqui estão os dados enviados pelo diagnóstico GhostAI:</p>

      <div class="section-title">Informações Básicas</div>
      <div class="box"><span class="label">Nome:</span> {data.get("nome","-")}</div>
      <div class="box"><span class="label">Email:</span> {data.get("email","-")}</div>
      <div class="box"><span class="label">WhatsApp:</span> {data.get("whatsapp","-")}</div>
      <div class="box"><span class="label">Empresa:</span> {data.get("empresa","-")}</div>

      <div class="section-title">Diagnóstico</div>
      <div class="box"><span class="label">Segmento:</span> {data.get("segmento","-")}</div>
      <div class="box"><span class="label">Volume diário:</span> {data.get("volume","-")}</div>
      <div class="box"><span class="label">Canais:</span> {", ".join(data.get("canal", []))}</div>
      <div class="box"><span class="label">Objetivos:</span> {", ".join(data.get("objetivo", []))}</div>

      <div class="section-title">Descrição</div>
      <div class="box">{data.get("descricao","(não informado)")}</div>

      <p>📎 O PDF completo está anexado a este e-mail.</p>

      <div class="footer">GhostAI • Automação Inteligente 👻</div>
    </div>

    </body>
    </html>
    """

    # ------------------ MONTAGEM E ENVIO ------------------
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
        logger.info("Email enviado com sucesso.")
    except Exception as e:
        logger.exception("Erro ao enviar email: %s")

# =====================================================================
# 📌 ROTA API - FORM
# =====================================================================
@app.post("/api/onboarding")
async def receive_form(request: Request):
    data = await request.json()
    save_data(data)
    send_email(data)
    return {"success": True, "redirect": "/success"}

# =====================================================================
# 📌 ROTA API - CHAT IA
# =====================================================================
@app.post("/api/chat")
async def api_chat(req: Request):
    payload = await req.json()
    msg = payload.get("message")
    history = payload.get("history", [])

    if not msg:
        raise HTTPException(400, "Mensagem é obrigatória")

    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "messages": history + [{"role": "user", "content": msg}]},
            timeout=8
        )
        reply = r.json().get("message", {}).get("content", "")
        return {"reply": reply}
    except:
        return {"reply": "IA indisponível no momento."}