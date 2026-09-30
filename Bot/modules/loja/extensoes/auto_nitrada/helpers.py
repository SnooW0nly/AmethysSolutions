"""
helpers.py — Funções centrais de acesso ao banco de dados do Nitro Automático
"""
from __future__ import annotations

import os
import uuid
import time
import asyncio
import logging
from typing import Optional, List, Dict, Any

from functions.database import database as db
from functions.emoji import emoji

logger = logging.getLogger("nitro_auto.helpers")

DB_CONFIG = "nitro_auto_config"
DB_CONTAS = "nitro_auto_contas"
DB_LINKS  = "nitro_auto_links"
DB_LOGS   = "nitro_auto_logs"

_lock_config = asyncio.Lock()
_lock_contas = asyncio.Lock()
_lock_logs   = asyncio.Lock()

# Stubs de compatibilidade — criptografia removida
def encrypt_sensitive(value: str) -> str: return value
def decrypt_sensitive(value: str) -> str: return value

# Bot ref para envio de logs no canal
_bot = None
def set_bot(bot): global _bot; _bot = bot

# ── Config ───────────────────────────────────────────────

def load_config() -> dict:
    data = db.get_document(DB_CONFIG) or {}
    data.setdefault("enabled",                  False)
    data.setdefault("workers",                  2)
    data.setdefault("delay_entre_contas",       3)
    data.setdefault("max_tentativas_por_conta", 3)
    data.setdefault("max_concurrent_requests",  3)
    data.setdefault("log_channel_id",           "")
    data.setdefault("total_processadas",        0)
    data.setdefault("total_nitradas",           0)
    data.setdefault("total_falhas",             0)
    data.setdefault("total_inelegiveis",        0)
    return data

def save_config(data: dict):
    db.save_document(DB_CONFIG, {}, data)

async def update_config_stat(campo: str, incremento: int = 1):
    async with _lock_config:
        cfg = load_config()
        cfg[campo] = cfg.get(campo, 0) + incremento
        save_config(cfg)

# ── Contas ───────────────────────────────────────────────

def load_contas() -> List[Dict]:
    return db.get_document(DB_CONTAS) or []

def save_contas(contas: List[Dict]):
    db.save_document(DB_CONTAS, {}, contas)

def _build_conta(token: str, email: str = "", senha: str = "") -> dict:
    return {
        "id":                str(uuid.uuid4())[:8],
        "token_raw":         token.strip(),
        "email":             email,
        "senha":             senha,
        "username":          "",
        "user_id":           "",
        "status":            "pendente",
        "elegivel":          None,
        "motivo_inelegivel": "",
        "tentativas":        0,
        "nitro_ativo":       False,
        "resultado":         {"sucesso": False, "link_usado": "", "expiracao_nitro": None},
        "worker_id":         None,
        "created_at":        int(time.time()),
    }

def add_conta(token: str, email: str = "", senha: str = "") -> str:
    contas = load_contas()
    if any(c.get("token_raw") == token.strip() for c in contas):
        return ""
    conta = _build_conta(token, email, senha)
    contas.append(conta)
    save_contas(contas)
    return conta["id"]

def add_contas_bulk(tokens: List[str], emails: List[str] = None, senhas: List[str] = None) -> int:
    contas = load_contas()
    existentes = {c.get("token_raw", "") for c in contas}
    added = 0
    for i, token in enumerate(tokens):
        token = token.strip()
        if not token or token in existentes:
            continue
        conta = _build_conta(
            token,
            emails[i] if emails and i < len(emails) else "",
            senhas[i]  if senhas  and i < len(senhas)  else ""
        )
        contas.append(conta)
        existentes.add(token)
        added += 1
    save_contas(contas)
    return added

def update_conta(conta_id: str, updates: dict):
    contas = load_contas()
    for c in contas:
        if c["id"] == conta_id:
            c.update(updates)
            break
    save_contas(contas)

def delete_conta(conta_id: str):
    contas = [c for c in load_contas() if c["id"] != conta_id]
    save_contas(contas)

def contar_contas_por_status() -> Dict[str, int]:
    counts = {"pendente": 0, "processando": 0, "nitrada": 0, "inelegivel": 0, "falha": 0}
    for c in load_contas():
        st = c.get("status", "pendente")
        counts[st] = counts.get(st, 0) + 1
    return counts

def exportar_contas_nitradas() -> List[Dict]:
    return [c for c in load_contas() if c["status"] == "nitrada"]

def limpar_contas_processadas():
    contas = [c for c in load_contas() if c["status"] in ("pendente", "processando")]
    save_contas(contas)

def reset_contas_travadas():
    contas = load_contas()
    resetadas = 0
    for c in contas:
        if c["status"] == "processando":
            c["status"] = "pendente"; c["worker_id"] = None; resetadas += 1
    if resetadas:
        save_contas(contas)
        logger.info(f"[Startup] {resetadas} contas desbloqueadas")
    return resetadas

async def get_proxima_conta_atomica() -> Optional[Dict]:
    async with _lock_contas:
        contas = load_contas()
        max_t  = load_config().get("max_tentativas_por_conta", 3)
        for c in contas:
            if c["status"] == "pendente" and c.get("tentativas", 0) < max_t:
                c["status"]     = "processando"
                c["tentativas"] = c.get("tentativas", 0) + 1
                save_contas(contas)
                return c
    return None

# ── Links ────────────────────────────────────────────────

def load_links() -> List[Dict]:
    return db.get_document(DB_LINKS) or []

def save_links(links: List[Dict]):
    db.save_document(DB_LINKS, {}, links)

def add_link(nome: str, url: str, parceiro: str, meses: int, plan_id: str = "", tipo: str = "link") -> str:
    links = load_links()
    lid   = str(uuid.uuid4())[:8]
    links.append({
        "id": lid, "nome": nome, "url": url, "parceiro": parceiro,
        "meses": meses, "plan_id": plan_id, "tipo": tipo,
        "ativo": True, "total_usado": 0, "ultimo_uso": None,
        "created_at": int(time.time())
    })
    save_links(links)
    return lid

def get_links_ativos() -> List[Dict]:
    return [l for l in load_links() if l.get("ativo", True)]

def update_link(link_id: str, updates: dict):
    links = load_links()
    for l in links:
        if l["id"] == link_id:
            l.update(updates); break
    save_links(links)

def delete_link(link_id: str):
    save_links([l for l in load_links() if l["id"] != link_id])

def incrementar_uso_link(link_id: str):
    links = load_links()
    for l in links:
        if l["id"] == link_id:
            l["total_usado"] = l.get("total_usado", 0) + 1
            l["ultimo_uso"]  = int(time.time()); break
    save_links(links)

# ── Logs ─────────────────────────────────────────────────

MAX_LOGS = 1000

LEVEL_COLORS = {
    "info":    0x5865F2,
    "success": 0x57F287,
    "error":   0xED4245,
    "warn":    0xFEE75C,
}
LEVEL_EMOJI = {"info": "ℹ️", "success": "✅", "error": "❌", "warn": "⚠️"}

def load_logs() -> List[Dict]:
    return db.get_document(DB_LOGS) or []

def save_logs(logs: List[Dict]):
    if len(logs) > MAX_LOGS:
        logs = logs[-MAX_LOGS:]
    db.save_document(DB_LOGS, {}, logs)

def add_log(level: str, mensagem: str, conta_id: str = "", link_id: str = "", worker_id: int = 0):
    import disnake
    from datetime import datetime

    entry = {
        "timestamp": int(time.time()),
        "level":     level,
        "mensagem":  mensagem,
        "conta_id":  conta_id,
        "link_id":   link_id,
        "worker_id": worker_id,
    }
    logs = load_logs()
    logs.append(entry)
    save_logs(logs)

    log_fn = getattr(logger, "warning" if level == "warn" else level, logger.info)
    try: log_fn(mensagem)
    except: logger.info(mensagem)

    # Envia no canal configurado
    if _bot:
        cfg        = load_config()
        channel_id = cfg.get("log_channel_id", "")
        if channel_id:
            async def _send():
                try:
                    ch = _bot.get_channel(int(channel_id))
                    if not ch:
                        return
                    icon  = LEVEL_EMOJI.get(level, "📝")
                    color = LEVEL_COLORS.get(level, 0x99aab5)
                    dt    = datetime.fromtimestamp(entry["timestamp"]).strftime("%d/%m %H:%M:%S")
                    desc  = mensagem
                    if conta_id: desc += f"\n-# Conta: `{conta_id}`"
                    if worker_id: desc += f" | Worker: `{worker_id}`"
                    embed = disnake.Embed(description=f"{icon} {desc}", color=color)
                    embed.set_footer(text=dt)
                    await ch.send(embed=embed)
                except Exception as e:
                    logger.debug(f"Falha ao enviar log no canal: {e}")
            asyncio.create_task(_send())

def get_logs_recentes(limit: int = 30, level: str = "") -> List[Dict]:
    logs = load_logs()
    if level:
        logs = [l for l in logs if l.get("level") == level]
    return list(reversed(logs[-limit:]))

def limpar_logs():
    save_logs([])
