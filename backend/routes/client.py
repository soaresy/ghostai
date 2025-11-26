# backend/routes/client.py
from fastapi import APIRouter, HTTPException
from fastapi import Depends
from pydantic import BaseModel, EmailStr

from core.security_user import get_admin_user
from services.client_service import (
    create_client, get_client, read_clients, update_client, delete_client
)

router = APIRouter(prefix="/api/clients", tags=["clients"])

class ClientCreate(BaseModel):
    nome: str
    email: EmailStr
    segmento: str = ""
    tema: dict = {}
    permissoes: dict = {}
    configuracoes: dict = {}

@router.post("/")
def create_cl(payload: ClientCreate, admin=Depends(get_admin_user)):
    return create_client(payload.dict())

@router.get("/")
def list_clients(admin=Depends(get_admin_user)):
    return read_clients()

@router.get("/{client_id}")
def get_client_route(client_id: str, admin=Depends(get_admin_user)):
    c = get_client(client_id)
    if not c:
        raise HTTPException(404, "Cliente não encontrado")
    return c

@router.put("/{client_id}")
def update_client_route(client_id: str, updates: dict, admin=Depends(get_admin_user)):
    updated = update_client(client_id, updates)
    if not updated:
        raise HTTPException(404, "Cliente não encontrado")
    return updated

@router.delete("/{client_id}")
def delete_client_route(client_id: str, admin=Depends(get_admin_user)):
    success = delete_client(client_id)
    return {"deleted": success}
