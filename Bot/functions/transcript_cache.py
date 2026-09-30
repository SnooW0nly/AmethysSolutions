import json
import os

DB_PATH = "database/tickets/transcript_data.json"

def _load_db():
    try:
        if not os.path.exists(DB_PATH):
            return {}
        with open(DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[CACHE] Erro ao carregar database: {e}")
        return {}

def _save_db(data):
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with open(DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[CACHE] Erro ao salvar database: {e}")

def get_cached_link(channel_id: int) -> str or None:
    """Retorna o link do transcript se estiver em cache."""
    db = _load_db()
    return db.get(str(channel_id))

def save_link_to_cache(channel_id: int, link: str):
    """Salva o link do transcript no cache."""
    db = _load_db()
    db[str(channel_id)] = link
    _save_db(db)

def delete_link_from_cache(channel_id: int):
    """Remove o link do transcript do cache."""
    db = _load_db()
    if str(channel_id) in db:
        del db[str(channel_id)]
        _save_db(db)
