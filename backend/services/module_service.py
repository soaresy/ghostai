# backend/services/module_service.py
from pathlib import Path
import json
import uuid

MODULES_FILE = Path(__file__).resolve().parents[2] / "data" / "modules.json"
MODULES_FILE.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_AVAILABLE_MODULES = [
    {"key": "whatsapp", "name": "WhatsApp Automations", "description": "Fluxos e envios via WhatsApp"},
    {"key": "instagram", "name": "Instagram DM", "description": "Automação de DMs e comentários"},
    {"key": "catalog", "name": "Catálogo", "description": "Gerenciar produtos"},
    {"key": "promotions", "name": "Promoções", "description": "Cupons e campanhas"},
    {"key": "analytics", "name": "Analytics", "description": "KPIs e relatórios"},
]

def _read_file():
    if not MODULES_FILE.exists():
        initial = {"available": DEFAULT_AVAILABLE_MODULES, "client_modules": {}}
        MODULES_FILE.write_text(json.dumps(initial, indent=2, ensure_ascii=False), "utf-8")
        return initial
    try:
        return json.loads(MODULES_FILE.read_text("utf-8"))
    except Exception:
        return {"available": DEFAULT_AVAILABLE_MODULES, "client_modules": {}}

def _write_file(data):
    MODULES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")

def list_available_modules():
    data = _read_file()
    return data.get("available", DEFAULT_AVAILABLE_MODULES)

def get_client_modules(client_id: str):
    data = _read_file()
    return data.get("client_modules", {}).get(client_id, {"enabled": []})

def set_client_modules(client_id: str, enabled_keys: list):
    data = _read_file()
    available = {m["key"] for m in data.get("available", [])}
    enabled = [k for k in enabled_keys if k in available]
    if "client_modules" not in data:
        data["client_modules"] = {}
    data["client_modules"][client_id] = {"enabled": enabled}
    _write_file(data)
    return data["client_modules"][client_id]

def enable_module_for_client(client_id: str, module_key: str):
    cfg = get_client_modules(client_id)
    if module_key not in cfg["enabled"]:
        cfg["enabled"].append(module_key)
    return set_client_modules(client_id, cfg["enabled"])

def disable_module_for_client(client_id: str, module_key: str):
    cfg = get_client_modules(client_id)
    if module_key in cfg["enabled"]:
        cfg["enabled"].remove(module_key)
    return set_client_modules(client_id, cfg["enabled"])
