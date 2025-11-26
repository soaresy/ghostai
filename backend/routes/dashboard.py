# backend/routes/dashboard.py
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from core.utils import read_json
from services.client_service import get_client_by_id
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from core.security import decode_access_token

router = APIRouter()
templates = Jinja2Templates(directory="backend/templates")
security = HTTPBearer()

def get_user_from_token(creds: HTTPAuthorizationCredentials):
    token = creds.credentials
    data = decode_access_token(token)
    return data

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, creds: HTTPAuthorizationCredentials = None):
    """
    Serve a dynamic dashboard page - front-end will call API for data.
    If token provided in Authorization, it uses that to render user-specific theme.
    """
    theme = {}
    client_data = {}
    if creds:
        try:
            data = get_user_from_token(creds)
            user_id = data.get("sub")
            # If you have mapping user->client, resolve it. For simplicity, assume user_id == client_id sometimes
            client_data = get_client_by_id(user_id) or {}
            theme = client_data.get("tema", {})
        except Exception:
            pass
    return templates.TemplateResponse("dashboard_template.html", {"request": request, "theme": theme, "client": client_data})
