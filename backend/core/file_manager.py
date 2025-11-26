# backend/core/file_manager.py
import os
from pathlib import Path
from werkzeug.utils import secure_filename  # for filename sanitization
from typing import Tuple

BASE_UPLOADS = Path(__file__).resolve().parents[1].parent / "frontend" / "dashboard" / "assets" / "user_uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "svg"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload(file, client_id: str) -> Tuple[bool, str]:
    """
    file is a Starlette UploadFile
    returns (success, relative_path)
    """
    if not file:
        return False, ""
    filename = secure_filename(file.filename)
    if not allowed_file(filename):
        return False, "file-type-not-allowed"
    upload_dir = BASE_UPLOADS / client_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    with open(dest, "wb") as f:
        content = file.file.read()
        f.write(content)
    # relative path for serving (adjust to your static route)
    rel = f"/static/uploads/{client_id}/{filename}"
    return True, rel
