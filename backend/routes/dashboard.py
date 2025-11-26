from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DASHBOARD = BASE_DIR / "frontend" / "dashboard"

@router.get("/dashboard")
def dashboard():
    return FileResponse(FRONTEND_DASHBOARD / "index.html")