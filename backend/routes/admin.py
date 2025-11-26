# backend/routes/admin.py
from fastapi import APIRouter, Depends
from core.security_user import get_admin_user
from services.account_service import read_users
from services.client_service import read_clients

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
def stats(admin=Depends(get_admin_user)):
    users = read_users()
    clients = read_clients()
    return {
        "total_users": len(users),
        "total_clients": len(clients),
    }

@router.get("/users")
def list_users(admin=Depends(get_admin_user)):
    users = read_users()
    for u in users:
        u.pop("password", None)
    return users

@router.get("/clients")
def list_clients(admin=Depends(get_admin_user)):
    return read_clients()
