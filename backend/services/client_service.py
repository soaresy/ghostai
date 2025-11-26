# backend/services/client_service.py
from pathlib import Path
import json
import uuid

CLIENTS_FILE = Path(__file__).resolve().parents[2] / "data" / "clients.json"
CLIENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

def read_clients():
    if CLIENTS_FILE.exists():
        try:
            return json.loads(CLIENTS_FILE.read_text("utf-8"))
        except:
            return []
    return []

def write_clients(data):
    CLIENTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")

def create_client(payload: dict):
    clients = read_clients()

    new_client = {
        "id": str(uuid.uuid4()),
        "nome": payload.get("nome"),
        "email": payload.get("email"),
        "segmento": payload.get("segmento", ""),
        "tema": payload.get("tema", {}),
        "permissoes": payload.get("permissoes", {}),
        "configuracoes": payload.get("configuracoes", {}),
        "created_at": payload.get("created_at"),
    }

    clients.append(new_client)
    write_clients(clients)
    return new_client

def get_client(client_id: str):
    return next((c for c in read_clients() if c["id"] == client_id), None)

def update_client(client_id: str, updates: dict):
    clients = read_clients()
    updated = None
    for i, c in enumerate(clients):
        if c["id"] == client_id:
            clients[i].update(updates)
            updated = clients[i]
    if updated:
        write_clients(clients)
    return updated

def delete_client(client_id: str):
    clients = read_clients()
    new_list = [c for c in clients if c["id"] != client_id]
    if len(new_list) == len(clients):
        return False
    write_clients(new_list)
    return True
