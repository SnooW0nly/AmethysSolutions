"""
helpers.py — Funções centrais do sistema de Entrar em Servidor (Mass Join via OAuth2)
"""
from __future__ import annotations

import uuid
import time
import secrets
import string
from typing import Optional, Any

from functions.database import database as db

DB_CONFIG_KEY   = "joiner_config"
DB_KEYS_KEY     = "joiner_keys"
DB_MEMBERS_KEY  = "joiner_members"
DB_LOGS_KEY     = "joiner_logs"
DB_GIFTS_KEY    = "joiner_gifts"
DB_TOKENS_KEY   = "joiner_account_tokens"

TOKENS_FILE_PATH = "database/extensions/impulso/tokens.json"


# ─────────────────────────────────────────────
#  Config global
# ─────────────────────────────────────────────

def load_config() -> dict:
    data = db.get_document(DB_CONFIG_KEY) or {}
    data.setdefault("enabled", False)
    data.setdefault("oauth_bot_token", "")
    data.setdefault("oauth_client_id", "")
    data.setdefault("oauth_client_secret", "")
    data.setdefault("target_guild_id", "")
    data.setdefault("target_guild_name", "")
    data.setdefault("verified_role_id", "")
    data.setdefault("log_channel_id", "")
    data.setdefault("trigger", {
        "key_panel_enabled": True,
        "key_chat_enabled": False,
        "key_slash_enabled": False,
        "slash_name": "entrar",
    })
    data.setdefault("messages", {
        "success_dm": "✅ Você foi adicionado ao servidor com sucesso!",
        "already_in_guild": "ℹ️ Você já está no servidor!",
        "invalid_key": "❌ Key inválida ou já utilizada.",
        "key_expired": "⌛ Esta key expirou.",
        "no_key_required": False,
    })
    data.setdefault("panel", {
        "channel_id": "",
        "message_id": "",
        "title": "Entrar no Servidor",
        "description": "Clique no botão abaixo para entrar em nosso servidor!",
        "button_label": "Entrar",
        "button_emoji": "🚀",
        "button_style": "green",
    })
    data.setdefault("key_prefix", "JOIN")
    data.setdefault("callback_path", "/joiner/callback")
    data.setdefault("oauth_panel_channel_id", "")
    return data


def save_config(data: dict):
    db.save_document(DB_CONFIG_KEY, data)


def get_api_base_url() -> str:
    """Retorna a URL base da API de extensões (Boost/Joiner) a partir das configurações centrais de API REST."""
    try:
        import json, os
        path = 'configs/config_api.json'
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            # Para chamadas REST do Joiner/Boost, usamos o endpoint de cloud/api definido no config_api.json
            url = cfg.get('cloud') or cfg.get('api')
            if url:
                return url.rstrip('/')
    except Exception:
        pass
    return 'https://amethyscloud.stackr.lat'


# ─────────────────────────────────────────────
#  Keys
# ─────────────────────────────────────────────

def _load_keys() -> dict:
    return db.get_document(DB_KEYS_KEY) or {"keys": {}}


def _save_keys(data: dict):
    db.save_document(DB_KEYS_KEY, data)


def generate_key(prefix: str = "JOIN", length: int = 12) -> str:
    chars = string.ascii_uppercase + string.digits
    return f"{prefix}-{''.join(secrets.choice(chars) for _ in range(length))}"


def create_keys(
    quantity: int,
    uses_per_key: int = 1,
    expires_at: Optional[int] = None,
    note: str = "",
    created_by_id: int = 0,
    created_by_name: str = "",
) -> list[str]:
    cfg = load_config()
    prefix = cfg.get("key_prefix", "JOIN")
    data = _load_keys()
    created = []
    for _ in range(quantity):
        key = generate_key(prefix)
        while key in data["keys"]:
            key = generate_key(prefix)
        data["keys"][key] = {
            "key": key,
            "uses": 0,
            "max_uses": uses_per_key,
            "expires_at": expires_at,
            "note": note,
            "used_by": [],
            "created_at": int(time.time()),
            "created_by": {"id": created_by_id, "name": created_by_name},
            "active": True,
        }
        created.append(key)
    _save_keys(data)
    return created


def get_key(key: str) -> Optional[dict]:
    data = _load_keys()
    return data["keys"].get(key)


def use_key(key: str, user_id: int) -> tuple[bool, str]:
    data = _load_keys()
    k = data["keys"].get(key)
    if not k:
        return False, "invalid"
    if not k.get("active", True):
        return False, "inactive"
    if k.get("expires_at") and int(time.time()) > k["expires_at"]:
        return False, "expired"
    if k["uses"] >= k["max_uses"]:
        return False, "used_up"
    if user_id in k.get("used_by", []):
        return False, "already_used"
    k["uses"] += 1
    k["used_by"].append(user_id)
    if k["uses"] >= k["max_uses"]:
        k["active"] = False
    _save_keys(data)
    return True, "ok"


def revoke_key(key: str) -> bool:
    data = _load_keys()
    if key not in data["keys"]:
        return False
    data["keys"][key]["active"] = False
    _save_keys(data)
    return True


def delete_key(key: str) -> bool:
    data = _load_keys()
    if key not in data["keys"]:
        return False
    del data["keys"][key]
    _save_keys(data)
    return True


def list_keys() -> list[dict]:
    data = _load_keys()
    return sorted(data["keys"].values(), key=lambda k: k.get("created_at", 0), reverse=True)


def get_key_stats() -> dict:
    keys = list_keys()
    active = [k for k in keys if k.get("active", True)]
    used_up = [k for k in keys if not k.get("active", True)]
    total_joins = sum(k.get("uses", 0) for k in keys)
    return {
        "total": len(keys),
        "active": len(active),
        "inactive": len(used_up),
        "total_joins": total_joins,
    }


# ─────────────────────────────────────────────
#  Members (OAuth tokens)
# ─────────────────────────────────────────────

def _load_members() -> dict:
    return db.get_document(DB_MEMBERS_KEY) or {"members": {}}


def _save_members(data: dict):
    db.save_document(DB_MEMBERS_KEY, data)


def save_member_token(
    discord_user_id: int,
    access_token: str,
    refresh_token: str,
    username: str,
    expires_in: int = 604800,
) -> dict:
    data = _load_members()
    member = {
        "discord_user_id": discord_user_id,
        "username": username,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": int(time.time()) + expires_in,
        "authorized_at": int(time.time()),
        "joined_guilds": [],
        "status": "authorized",
    }
    data["members"][str(discord_user_id)] = member
    _save_members(data)
    return member


def get_member_token(discord_user_id: int) -> Optional[dict]:
    data = _load_members()
    return data["members"].get(str(discord_user_id))


def mark_member_joined(discord_user_id: int, guild_id: str):
    data = _load_members()
    m = data["members"].get(str(discord_user_id))
    if m and guild_id not in m.get("joined_guilds", []):
        m.setdefault("joined_guilds", []).append(guild_id)
        _save_members(data)


def count_members() -> int:
    return len(_load_members()["members"])


def get_all_members() -> list[dict]:
    data = _load_members()
    return list(data["members"].values())


# ─────────────────────────────────────────────
#  OAuth state store (CSRF protection)
# ─────────────────────────────────────────────

_oauth_states: dict[str, dict] = {}


def create_oauth_state(user_id: int, key: Optional[str] = None) -> str:
    """
    Gera um state OAuth2 no formato "<api_key>:<uuid>" para suporte multi-tenant.
    """
    from functions.database import database as db
    cloud_data = db.get_document("cloud_data") or {}
    api_key = cloud_data.get("api_key", "")

    inner_state = secrets.token_urlsafe(32)
    state = f"{api_key}:{inner_state}" if api_key else inner_state

    _oauth_states[state] = {
        "user_id": user_id,
        "key": key,
        "created_at": time.time(),
    }
    cutoff = time.time() - 600
    to_del = [s for s, v in _oauth_states.items() if v["created_at"] < cutoff]
    for s in to_del:
        _oauth_states.pop(s, None)
    return state


def consume_oauth_state(state: str) -> Optional[dict]:
    val = _oauth_states.pop(state, None)
    if val:
        if (time.time() - val["created_at"]) > 600:
            return None
        return val

    for full_state, data in list(_oauth_states.items()):
        if full_state.endswith(f":{state}") or full_state == state:
            _oauth_states.pop(full_state, None)
            if (time.time() - data["created_at"]) > 600:
                return None
            return data

    return None


# ─────────────────────────────────────────────
#  Gift stats (para painéis — dados vêm do JS via WS)
# ─────────────────────────────────────────────

def get_gift_stats() -> dict:
    """Stats locais — o painel de gifts usa WS para dados em tempo real."""
    return {"total": 0, "redeemed": 0, "pending": 0}


# ─────────────────────────────────────────────
#  Account Tokens
# ─────────────────────────────────────────────

import os
import json as _json


def _tokens_file_path() -> str:
    return TOKENS_FILE_PATH


def _load_account_tokens() -> dict:
    fpath = _tokens_file_path()
    if os.path.exists(fpath):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = _json.load(f)
                if isinstance(data, list):
                    return {"tokens": {str(i): {"token": t, "index": i} if isinstance(t, str) else t
                                       for i, t in enumerate(data)}}
                if isinstance(data, dict) and "tokens" in data:
                    return data
        except Exception:
            pass
    return db.get_document(DB_TOKENS_KEY) or {"tokens": {}}


def _save_account_tokens(data: dict):
    db.save_document(DB_TOKENS_KEY, data)
    fpath = _tokens_file_path()
    try:
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as f:
            _json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_account_token(token: str, label: str = "", added_by_id: int = 0) -> str:
    data = _load_account_tokens()
    token_id = secrets.token_hex(8)
    while token_id in data["tokens"]:
        token_id = secrets.token_hex(8)
    data["tokens"][token_id] = {
        "token_id": token_id,
        "token": token,
        "label": label,
        "added_by": added_by_id,
        "added_at": int(time.time()),
        "linked_oauth_user_id": None,
        "linked_at": None,
        "status": "pending",
    }
    _save_account_tokens(data)
    return token_id


def get_account_token(token_id: str) -> Optional[dict]:
    data = _load_account_tokens()
    return data["tokens"].get(token_id)


def get_account_token_by_value(token: str) -> Optional[dict]:
    data = _load_account_tokens()
    for t in data["tokens"].values():
        if t.get("token") == token:
            return t
    return None


def list_account_tokens() -> list[dict]:
    data = _load_account_tokens()
    return sorted(data["tokens"].values(), key=lambda t: t.get("added_at", 0), reverse=True)


def delete_account_token(token_id: str) -> bool:
    data = _load_account_tokens()
    if token_id not in data["tokens"]:
        return False
    del data["tokens"][token_id]
    _save_account_tokens(data)
    return True


def link_token_to_oauth(token_id: str, discord_user_id: int) -> bool:
    data = _load_account_tokens()
    t = data["tokens"].get(token_id)
    if not t:
        return False
    t["linked_oauth_user_id"] = discord_user_id
    t["linked_at"] = int(time.time())
    t["status"] = "linked"
    _save_account_tokens(data)
    return True


def get_token_linked_to_oauth(discord_user_id: int) -> Optional[dict]:
    data = _load_account_tokens()
    for t in data["tokens"].values():
        if t.get("linked_oauth_user_id") == discord_user_id:
            return t
    return None


def get_unlinked_account_tokens() -> list[dict]:
    data = _load_account_tokens()
    return [t for t in data["tokens"].values() if not t.get("linked_oauth_user_id")]


def count_account_tokens() -> dict:
    tokens = list_account_tokens()
    linked = [t for t in tokens if t.get("status") == "linked"]
    pending = [t for t in tokens if t.get("status") == "pending"]
    cache = [t for t in tokens if t.get("status") == "cache"]
    return {"total": len(tokens), "linked": len(linked), "pending": len(pending), "cache": len(cache)}


# ─────────────────────────────────────────────
#  OAuth Cache
# ─────────────────────────────────────────────

def _load_oauth_cache() -> dict:
    return db.get_document("joiner_oauth_cache") or {"cache": {}}


def _save_oauth_cache(data: dict):
    db.save_document("joiner_oauth_cache", data)


def cache_oauth_credentials(
    discord_user_id: int,
    username: str,
    access_token: str,
    refresh_token: str,
    expires_in: int = 604800,
) -> str:
    data = _load_oauth_cache()
    cache_id = str(discord_user_id)
    data["cache"][cache_id] = {
        "cache_id": cache_id,
        "discord_user_id": discord_user_id,
        "username": username,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_expires_at": int(time.time()) + expires_in,
        "cached_at": int(time.time()),
        "status": "waiting_token",
    }
    _save_oauth_cache(data)
    return cache_id


def get_oauth_cache(discord_user_id: int) -> Optional[dict]:
    data = _load_oauth_cache()
    return data["cache"].get(str(discord_user_id))


def consume_oauth_cache(discord_user_id: int) -> Optional[dict]:
    data = _load_oauth_cache()
    entry = data["cache"].pop(str(discord_user_id), None)
    if entry:
        _save_oauth_cache(data)
    return entry


def try_link_pending_oauth(token_id: str) -> Optional[int]:
    cache_data = _load_oauth_cache()
    waiting = [v for v in cache_data["cache"].values() if v.get("status") == "waiting_token"]
    if not waiting:
        return None
    oldest = sorted(waiting, key=lambda x: x.get("cached_at", 0))[0]
    discord_user_id = oldest["discord_user_id"]

    link_token_to_oauth(token_id, discord_user_id)

    save_member_token(
        discord_user_id=discord_user_id,
        access_token=oldest["access_token"],
        refresh_token=oldest["refresh_token"],
        username=oldest["username"],
        expires_in=max(0, oldest["token_expires_at"] - int(time.time())),
    )

    cache_data["cache"].pop(str(discord_user_id), None)
    _save_oauth_cache(cache_data)

    return discord_user_id


def get_linked_tokens_for_boost() -> list[dict]:
    data = _load_account_tokens()
    members_data = _load_members()
    result = []
    for t in data["tokens"].values():
        if t.get("status") != "linked" or not t.get("linked_oauth_user_id"):
            continue
        uid = str(t["linked_oauth_user_id"])
        member = members_data["members"].get(uid, {})
        result.append({
            "token_id": t["token_id"],
            "token": t.get("token", ""),
            "label": t.get("label", ""),
            "linked_oauth_user_id": t["linked_oauth_user_id"],
            "username": member.get("username", t.get("label", "")),
            "access_token": member.get("access_token", ""),
            "refresh_token": member.get("refresh_token", ""),
            "token_expires_at": member.get("token_expires_at", 0),
        })
    return result


# ─────────────────────────────────────────────
#  Logs
# ─────────────────────────────────────────────

def log_join(user_id: int, username: str, guild_id: str, key: Optional[str], success: bool, reason: str = ""):
    logs_data = db.get_document(DB_LOGS_KEY) or {"logs": []}
    logs_data.setdefault("logs", [])
    logs_data["logs"].append({
        "user_id": user_id,
        "username": username,
        "guild_id": guild_id,
        "key": key,
        "success": success,
        "reason": reason,
        "timestamp": int(time.time()),
    })
    logs_data["logs"] = logs_data["logs"][-1000:]
    db.save_document(DB_LOGS_KEY, logs_data)


def get_recent_logs(limit: int = 20) -> list[dict]:
    logs_data = db.get_document(DB_LOGS_KEY) or {"logs": []}
    logs = logs_data.get("logs", [])
    return list(reversed(logs[-limit:]))
