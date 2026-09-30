from functions.database import database as db
import uuid
import asyncio
import aiohttp
import disnake
from typing import Optional, List, Dict
import requests  # para validação síncrona
import time

# ─── Config helpers ────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.obter("database/automations/disparador_dm.json") or {}
    dados.setdefault("ativado", False)
    dados.setdefault("tokens", [])
    dados.setdefault("mensagem", {})
    return dados

def salvar_config(data: dict) -> None:
    db.salvar("database/automations/disparador_dm.json", data)

# ─── Temp DB com writes em lote ────────────────────────────────────────────────
# Em vez de salvar no disco a cada usuário enviado (killer de performance),
# mantemos um cache em memória e fazemos flush periódico.

_temp_db_cache: dict | None = None
_temp_db_dirty: bool = False

def carregar_temp_db() -> dict:
    global _temp_db_cache
    if _temp_db_cache is None:
        try:
            dados = db.obter("database/automations/temp_disparador_dm.json") or {}
        except Exception:
            dados = {}
        dados.setdefault("usuarios_alvo", [])
        dados.setdefault("usuarios_enviados", [])
        dados.setdefault("tokens_falhos", [])
        dados.setdefault("usuarios_falhos", [])
        _temp_db_cache = dados
    return _temp_db_cache

def _flush_temp_db() -> None:
    """Persiste o cache no disco. Chame explicitamente quando necessário."""
    global _temp_db_dirty
    if _temp_db_cache is not None and _temp_db_dirty:
        db.salvar("database/automations/temp_disparador_dm.json", _temp_db_cache)
        _temp_db_dirty = False

def salvar_temp_db(data: dict) -> None:
    global _temp_db_cache, _temp_db_dirty
    _temp_db_cache = data
    _temp_db_dirty = True
    _flush_temp_db()  # flush imediato em operações explícitas (limpar, etc.)

def limpar_temp_db() -> None:
    global _temp_db_cache, _temp_db_dirty
    _temp_db_cache = {"usuarios_alvo": [], "usuarios_enviados": [], "tokens_falhos": [], "usuarios_falhos": []}
    _temp_db_dirty = True
    _flush_temp_db()

# ─── Token helpers ─────────────────────────────────────────────────────────────

async def validar_token_async(session: aiohttp.ClientSession, token: str) -> bool:
    try:
        async with session.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=aiohttp.ClientTimeout(total=5)
        ) as r:
            return r.status == 200
    except Exception:
        return False

def validar_token(token: str) -> bool:
    """Versão síncrona para uso fora de contexto async."""
    try:
        r = requests.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {token}"},
            timeout=5
        )
        return r.status_code == 200
    except Exception:
        return False

def obter_bot_info(token: str) -> Optional[Dict]:
    try:
        r = requests.get("https://discord.com/api/v10/users/@me",
                         headers={"Authorization": f"Bot {token}"}, timeout=5)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

def validar_tokens(tokens: List[str]) -> tuple[int, int]:
    total = len(tokens)
    validos = sum(1 for t in tokens if validar_token(t))
    return total, validos

# ─── Editor helpers ────────────────────────────────────────────────────────────

def set_editor_field(field: str, value):
    config = carregar_config()
    config["mensagem"][field] = value
    salvar_config(config)

def get_editor_data() -> dict:
    return carregar_config().get("mensagem", {})

def clear_editor_field(field: str):
    config = carregar_config()
    if field in config.get("mensagem", {}):
        del config["mensagem"][field]
        salvar_config(config)
        return True
    return False

def set_editor_data(editor_data: dict):
    config = carregar_config()
    config["mensagem"] = editor_data
    salvar_config(config)

# ─── Usuários helpers (cache-aware, sem I/O por iteração) ──────────────────────

def adicionar_usuario_enviado_bulk(user_ids: List[int]) -> None:
    """Adiciona múltiplos usuários de uma vez — chame periodicamente, não a cada envio."""
    global _temp_db_dirty
    db_data = carregar_temp_db()
    enviados_set = set(db_data["usuarios_enviados"])
    enviados_set.update(user_ids)
    db_data["usuarios_enviados"] = list(enviados_set)
    _temp_db_dirty = True

def adicionar_usuario_falho_bulk(user_ids: List[int]) -> None:
    global _temp_db_dirty
    db_data = carregar_temp_db()
    falhos_set = set(db_data["usuarios_falhos"])
    falhos_set.update(user_ids)
    db_data["usuarios_falhos"] = list(falhos_set)
    _temp_db_dirty = True

def flush_progresso() -> None:
    """Persiste progresso acumulado no disco."""
    _flush_temp_db()

def adicionar_usuario_enviado(user_id: int):
    global _temp_db_dirty
    db_data = carregar_temp_db()
    if user_id not in db_data["usuarios_enviados"]:
        db_data["usuarios_enviados"].append(user_id)
        _temp_db_dirty = True

def adicionar_usuario_falho(user_id: int):
    global _temp_db_dirty
    db_data = carregar_temp_db()
    if user_id not in db_data["usuarios_falhos"]:
        db_data["usuarios_falhos"].append(user_id)
        _temp_db_dirty = True

def get_usuarios_pendentes() -> List[int]:
    db_data = carregar_temp_db()
    alvo = set(db_data.get("usuarios_alvo", []))
    enviados = set(db_data.get("usuarios_enviados", []))
    falhos = set(db_data.get("usuarios_falhos", []))
    return list(alvo - enviados - falhos)

def salvar_usuarios_alvo(usuarios: List[int]):
    global _temp_db_dirty
    db_data = carregar_temp_db()
    db_data["usuarios_alvo"] = usuarios
    _temp_db_dirty = True
    _flush_temp_db()

# ─── Token falhos ──────────────────────────────────────────────────────────────

def adicionar_token_falho(token: str, motivo: str = "Erro ao enviar mensagens"):
    global _temp_db_dirty
    db_data = carregar_temp_db()
    tokens_falhos = db_data.get("tokens_falhos", [])
    if any(t.get("token") == token for t in tokens_falhos):
        return
    token_mascarado = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else token[:10] + "..."
    tokens_falhos.append({
        "token": token,
        "token_mascarado": token_mascarado,
        "motivo": motivo,
        "timestamp": int(time.time())
    })
    db_data["tokens_falhos"] = tokens_falhos
    _temp_db_dirty = True
    _flush_temp_db()  # Falho de token é crítico, persistir imediatamente

def obter_tokens_falhos() -> List[Dict]:
    return carregar_temp_db().get("tokens_falhos", [])

def remover_token_do_config(token: str) -> bool:
    try:
        config = carregar_config()
        tokens = config.get("tokens", [])
        if token in tokens:
            tokens.remove(token)
            config["tokens"] = tokens
            salvar_config(config)
            return True
        return False
    except Exception as e:
        print(f"Erro ao remover token: {e}")
        return False

def limpar_tokens_falhos() -> None:
    global _temp_db_dirty
    db_data = carregar_temp_db()
    db_data["tokens_falhos"] = []
    _temp_db_dirty = True
    _flush_temp_db()

# ─── Mapear usuários ───────────────────────────────────────────────────────────

async def mapear_usuarios_alvo(bot, server_id, role_id, exclude_roles, exclude_users) -> List[int]:
    try:
        if server_id:
            guild = bot.get_guild(int(server_id))
        else:
            guild = bot.guilds[0] if bot.guilds else None
        if not guild:
            return []

        exclude_role_ids = {int(rid) for rid in exclude_roles if rid.strip()}
        exclude_user_ids = {int(uid) for uid in exclude_users if uid.strip()}

        if not role_id or not role_id.strip():
            members = guild.members
        else:
            role = guild.get_role(int(role_id))
            if not role:
                return []
            members = role.members

        return [
            m.id for m in members
            if not m.bot
            and m.id not in exclude_user_ids
            and not any(r.id in exclude_role_ids for r in m.roles)
        ]
    except Exception as e:
        print(f"Erro ao mapear usuários alvo: {e}")
        return []
