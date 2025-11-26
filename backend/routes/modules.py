# backend/routes/modules.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from core.security_user import get_current_user, get_admin_user
from services.module_service import (
    list_available_modules,
    get_client_modules,
    set_client_modules,
    enable_module_for_client,
    disable_module_for_client,
)
from services.client_service import read_clients, get_client

router = APIRouter(prefix="/api/modules", tags=["modules"])

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

@router.get("/available")
def available():
    return {"available": list_available_modules()}

@router.get("/me")
def client_modules(user=Depends(get_current_user)):
    client_id = _resolve_client_id_from_user(user)
    if not client_id:
        raise HTTPException(status_code=404, detail="Cliente não encontrado para este usuário")
    return {"client_id": client_id, "modules": get_client_modules(client_id)}

@router.get("/client/{client_id}")
def client_modules_admin(client_id: str, admin=Depends(get_admin_user)):
    c = get_client(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"client": c, "modules": get_client_modules(client_id)}

@router.put("/client/{client_id}")
def set_modules(client_id: str, payload: Dict, admin=Depends(get_admin_user)):
    enabled = payload.get("enabled", [])
    if not isinstance(enabled, list):
        raise HTTPException(status_code=400, detail="enabled deve ser uma lista")
    cfg = set_client_modules(client_id, enabled)
    return {"client_id": client_id, "modules": cfg}

@router.post("/client/{client_id}/enable/{module_key}")
def enable_module(client_id: str, module_key: str, admin=Depends(get_admin_user)):
    cfg = enable_module_for_client(client_id, module_key)
    return {"client_id": client_id, "modules": cfg}

@router.post("/client/{client_id}/disable/{module_key}")
def disable_module(client_id: str, module_key: str, admin=Depends(get_admin_user)):
    cfg = disable_module_for_client(client_id, module_key)
    return {"client_id": client_id, "modules": cfg}
