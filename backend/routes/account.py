# backend/routes/account.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from core.security_user import get_current_user
from services.account_service import update_user, change_user_password
from backend.core.file_manager import save_upload

router = APIRouter(prefix="/api/account", tags=["account"])

# ---------------- GET PERFIL ----------------

@router.get("/me")
def get_profile(user=Depends(get_current_user)):
    return user

# ---------------- UPDATE PERFIL ----------------

@router.put("/update")
def update_profile(payload: dict, user=Depends(get_current_user)):

    allowed = {"name", "empresa", "bio"}

    updates = {k: v for k, v in payload.items() if k in allowed}

    updated = update_user(user["id"], updates)

    if not updated:
        raise HTTPException(400, "Não foi possível atualizar o perfil.")

    updated.pop("password", None)
    return updated

# ---------------- TROCAR SENHA ----------------

@router.put("/change-password")
def update_password(payload: dict, user=Depends(get_current_user)):

    new_password = payload.get("new_password")

    if not new_password or len(new_password) < 6:
        raise HTTPException(400, "Senha deve ter 6+ caracteres.")

    ok = change_user_password(user["id"], new_password)
    return {"success": ok}

# ---------------- AVATAR ----------------

@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), user=Depends(get_current_user)):

    ok, path = save_upload(file, user["id"])

    if not ok:
        raise HTTPException(400, "Formato não permitido")

    update_user(user["id"], {"avatar": path})

    return {"avatar": path}
