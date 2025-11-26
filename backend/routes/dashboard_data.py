# backend/routes/dashboard_data.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from core.security_user import get_current_user, get_admin_user
from services.client_service import get_client, read_clients
from services.module_service import get_client_modules, list_available_modules

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

def _resolve_client_id_from_user(user: Dict):
    if user.get("client_id"):
        return user.get("client_id")
    empresa = (user.get("empresa") or "").strip().lower()
    if not empresa:
        return None
    for c in read_clients():
        if (c.get("nome") or "").strip().lower() == empresa or (c.get("email") or "").strip().lower() == empresa:
            return c.get("id")
    return None

@router.get("/data")
def dashboard_data(user=Depends(get_current_user)):
    client_id = _resolve_client_id_from_user(user)
    if not client_id:
        if user.get("role") == "admin":
            clients = read_clients()
            if not clients:
                raise HTTPException(status_code=404, detail="Nenhum cliente cadastrado")
            client_id = clients[0].get("id")
        else:
            raise HTTPException(status_code=404, detail="Cliente não encontrado para este usuário")

    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    modules_cfg = get_client_modules(client_id)
    available = list_available_modules()

    kpis = {
        "leads_last_7_days": 0,
        "conversions_last_7_days": 0,
        "open_chats": 0
    }

    return {
        "client": {
            "id": client.get("id"),
            "nome": client.get("nome"),
            "tema": client.get("tema", {}),
            "logo": client.get("tema", {}).get("logo"),
        },
        "modules": modules_cfg,
        "available_modules": available,
        "user": {k:v for k,v in user.items() if k != "password"},
        "kpis": kpis
    }

@router.get("/client/{client_id}")
def dashboard_data_admin(client_id: str, admin=Depends(get_admin_user)):
    client = get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    modules_cfg = get_client_modules(client_id)
    return {"client": client, "modules": modules_cfg}
