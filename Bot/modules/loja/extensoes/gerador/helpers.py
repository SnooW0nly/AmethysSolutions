"""
helpers.py — Funções centrais de acesso ao banco de dados do Gerador
"""
from __future__ import annotations

import uuid
import time
from typing import Optional, Any

from functions.database import database as db

DB_KEY = "gerador_config"
DB_STOCK_KEY = "gerador_stock"
DB_LOGS_KEY = "gerador_logs"


# ─────────────────────────────────────────────
#  Config global
# ─────────────────────────────────────────────

def load_config() -> dict:
    data = db.get_document(DB_KEY) or {}
    data.setdefault("enabled", False)
    data.setdefault("grupos", {})        # grupos de serviços (ex: Free, VIP, Premium)
    data.setdefault("servicos", {})      # serviços individuais
    data.setdefault("trigger", {
        "type": "prefix",               # "prefix" | "slash" | "channel"
        "prefix": "+",
        "canal_id": None,
        "slash_name": "gen",
    })
    data.setdefault("config", {
        "canal_log_id": None,
        "canal_gen_id": None,           # canal onde gera (modo channel)
        "cargo_admin_id": None,
        "cooldown_segundos": 0,
        "max_por_dia": 0,               # 0 = ilimitado
        "enviar_dm": True,              # True = DM, False = canal
        "apagar_mensagem_trigger": True,
        "mostrar_quem_gerou": True,
    })
    return data


def save_config(data: dict):
    db.save_document(DB_KEY, {}, data)


# ─────────────────────────────────────────────
#  Serviços
# ─────────────────────────────────────────────

def get_service(service_id: str) -> Optional[dict]:
    config = load_config()
    return config["servicos"].get(service_id)


def list_services() -> dict:
    return load_config()["servicos"]


def create_service(nome: str, grupo_id: Optional[str] = None) -> str:
    config = load_config()
    sid = str(uuid.uuid4())[:8]
    while sid in config["servicos"]:
        sid = str(uuid.uuid4())[:8]

    config["servicos"][sid] = {
        "id": sid,
        "nome": nome,
        "alias": [nome.lower()],        # palavras-chave para trigger
        "grupo_id": grupo_id,
        "ativo": True,
        "descricao": "",
        "imagem_url": "",
        "cor_hex": "",
        # Mensagem de entrega (builder-compatible)
        "mensagem": {
            "content": None,
            "embed": {"title": None, "description": None, "color": None, "footer": None, "banner": None},
            "container": None,
            "externalImage": None,
        },
        # Mensagem sem estoque
        "mensagem_sem_estoque": {
            "content": None,
            "embed": {"title": None, "description": None, "color": None},
            "container": None,
        },
        # Stock fake
        "stock_fake": {
            "enabled": False,
            "mensagem_fake": None,
        },
        # Permissões
        "cargos_permitidos": [],        # [] = todos
        "cargos_bloqueados": [],
        "canais_permitidos": [],        # [] = todos
        "canais_bloqueados": [],
        # Configurações de entrega
        "enviar_dm": None,              # None = herda global
        "apagar_trigger": None,         # None = herda global
        "mostrar_quem_gerou": None,     # None = herda global
        "cooldown_segundos": None,      # None = herda global
        "max_por_dia": None,            # None = herda global
        # Estatísticas
        "total_gerado": 0,
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
    }
    save_config(config)
    return sid


def update_service(service_id: str, updates: dict):
    config = load_config()
    if service_id not in config["servicos"]:
        return False
    config["servicos"][service_id].update(updates)
    config["servicos"][service_id]["updated_at"] = int(time.time())
    save_config(config)
    return True


def delete_service(service_id: str):
    config = load_config()
    config["servicos"].pop(service_id, None)
    # Limpar estoque
    stock = load_stock()
    stock.pop(service_id, None)
    save_stock(stock)
    save_config(config)


# ─────────────────────────────────────────────
#  Grupos
# ─────────────────────────────────────────────

def create_group(nome: str) -> str:
    config = load_config()
    gid = str(uuid.uuid4())[:8]
    while gid in config["grupos"]:
        gid = str(uuid.uuid4())[:8]
    config["grupos"][gid] = {
        "id": gid,
        "nome": nome,
        "descricao": "",
        "cor_hex": "",
        "created_at": int(time.time()),
    }
    save_config(config)
    return gid


def list_groups() -> dict:
    return load_config()["grupos"]


def delete_group(group_id: str):
    config = load_config()
    config["grupos"].pop(group_id, None)
    # Desassociar serviços
    for sid, svc in config["servicos"].items():
        if svc.get("grupo_id") == group_id:
            svc["grupo_id"] = None
    save_config(config)


# ─────────────────────────────────────────────
#  Estoque
# ─────────────────────────────────────────────

def load_stock() -> dict:
    return db.get_document(DB_STOCK_KEY) or {}


def save_stock(data: dict):
    db.save_document(DB_STOCK_KEY, {}, data)


def add_stock_items(service_id: str, items: list[str]) -> int:
    stock = load_stock()
    stock.setdefault(service_id, [])
    stock[service_id].extend(items)
    save_stock(stock)
    return len(stock[service_id])


def get_stock_count(service_id: str) -> int:
    stock = load_stock()
    return len(stock.get(service_id, []))


def pop_stock_item(service_id: str) -> Optional[str]:
    """Remove e retorna o próximo item do estoque."""
    stock = load_stock()
    items = stock.get(service_id, [])
    if not items:
        return None
    item = items.pop(0)
    stock[service_id] = items
    save_stock(stock)
    return item


def clear_stock(service_id: str):
    stock = load_stock()
    stock[service_id] = []
    save_stock(stock)


def get_all_stock_items(service_id: str) -> list[str]:
    return load_stock().get(service_id, [])


# ─────────────────────────────────────────────
#  Cooldown / limite diário (em memória — simples)
# ─────────────────────────────────────────────

_cooldowns: dict[str, float] = {}       # "user_id:service_id" -> timestamp
_daily_count: dict[str, int] = {}       # "user_id:service_id:YYYY-MM-DD" -> count


def check_cooldown(user_id: int, service_id: str, seconds: int) -> float:
    """Retorna segundos restantes, 0 se liberado."""
    if seconds <= 0:
        return 0
    key = f"{user_id}:{service_id}"
    last = _cooldowns.get(key, 0)
    remaining = (last + seconds) - time.time()
    return max(remaining, 0)


def set_cooldown(user_id: int, service_id: str):
    _cooldowns[f"{user_id}:{service_id}"] = time.time()


def check_daily_limit(user_id: int, service_id: str, limit: int) -> bool:
    """Retorna True se pode gerar, False se atingiu o limite."""
    if limit <= 0:
        return True
    from datetime import date
    day = str(date.today())
    key = f"{user_id}:{service_id}:{day}"
    return _daily_count.get(key, 0) < limit


def increment_daily(user_id: int, service_id: str):
    from datetime import date
    day = str(date.today())
    key = f"{user_id}:{service_id}:{day}"
    _daily_count[key] = _daily_count.get(key, 0) + 1


# ─────────────────────────────────────────────
#  Logs
# ─────────────────────────────────────────────

def log_generation(user_id: int, service_id: str, service_name: str, item: str, guild_id: int):
    logs = db.get_document(DB_LOGS_KEY) or {"logs": []}
    logs.setdefault("logs", [])
    logs["logs"].append({
        "user_id": user_id,
        "service_id": service_id,
        "service_name": service_name,
        "item_preview": item[:20] + "..." if len(item) > 20 else item,
        "guild_id": guild_id,
        "timestamp": int(time.time()),
    })
    # Manter apenas últimos 500 logs
    logs["logs"] = logs["logs"][-500:]
    db.save_document(DB_LOGS_KEY, {}, logs)
