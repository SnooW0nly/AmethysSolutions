"""
modules/utilitarios/comunidade/tagbio/helpers.py

Config, DB helpers, log helpers e builders de UI do sistema Cargo por Tag/Bio.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Optional

import disnake

from functions.database import database as db
from functions.emoji import emoji

DB_KEY = "utilitarios_tagbio"


# ─── Config ───────────────────────────────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document(DB_KEY) or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("ativado", False)
    dados.setdefault("tag_ativo", False)
    dados.setdefault("bio_ativo", False)
    dados.setdefault("cargo_id", None)
    dados.setdefault("cooldown_minutos", 60)
    dados.setdefault("canal_logs_publico_id", None)
    dados.setdefault("canal_logs_privado_id", None)
    dados.setdefault("tag_texto", None)           # texto que deve estar na tag
    dados.setdefault("bio_texto", None)           # texto que deve estar na bio
    dados.setdefault("mensagem", {})              # editor_data da mensagem (igual MsgAuto)
    return dados


def salvar_config(data: dict) -> None:
    atual = carregar_config()
    atual.update(data or {})
    db.save_document(DB_KEY, {}, atual)


# ─── Tokens de usuário (igual padrão Tokens cog) ──────────────────────────────

def _tokens_list() -> list[dict]:
    doc = db.get_document("tokens") or {}
    return doc.get("list", [])


def get_user_token(user_id: str | int) -> str | None:
    """Retorna o token de usuário cadastrado para o user_id, ou None."""
    uid = str(user_id)
    for t in _tokens_list():
        if str(t.get("user_id")) == uid:
            return t.get("token")
    return None


def get_any_token() -> str | None:
    """Retorna o primeiro token de usuário disponível na lista."""
    tokens = _tokens_list()
    if tokens:
        return tokens[0].get("token")
    return None


# ─── Token do bot (config.json) ───────────────────────────────────────────────

def get_bot_token() -> str | None:
    try:
        config = db.obter("config.json")
        return config.get("bot", {}).get("token")
    except Exception:
        pass
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f).get("bot", {}).get("token")
    except Exception:
        return None


# ─── UI helpers ───────────────────────────────────────────────────────────────

def accent(primary_hex: str | None) -> dict:
    if primary_hex:
        return {"accent_colour": disnake.Colour(int(primary_hex.replace("#", ""), 16))}
    return {}


def color(primary_hex: str | None) -> disnake.Colour | None:
    if primary_hex:
        return disnake.Colour(int(primary_hex.replace("#", ""), 16))
    return None


def _primary_hex() -> str | None:
    return (db.get_document("custom_colors") or {}).get("primary")


def _mode() -> str:
    return (db.get_document("custom_mode") or {}).get("mode", "components")


# ─── Editor de mensagem (mesmo padrão MsgAuto) ────────────────────────────────

def get_mensagem_data() -> dict:
    return carregar_config().get("mensagem", {})


def set_mensagem_data(data: dict) -> None:
    config = carregar_config()
    config["mensagem"] = data
    salvar_config(config)


def clear_mensagem_field(field: str) -> None:
    data = get_mensagem_data()
    if field == "embed":
        data.pop("embed", None)
    elif field == "content":
        data.pop("content", None)
    elif field == "container":
        data.pop("container", None)
    elif field == "externalImage":
        data.pop("externalImage", None)
        data.get("embed", {}).pop("banner", None)
        data.get("embed", {}).pop("thumbnail", None)
    set_mensagem_data(data)


# ─── Log helpers ──────────────────────────────────────────────────────────────

async def _get_canal(bot, canal_id: str | int | None) -> disnake.TextChannel | None:
    if not canal_id:
        return None
    try:
        canal = bot.get_channel(int(canal_id))
        if isinstance(canal, disnake.TextChannel):
            return canal
    except (ValueError, AttributeError):
        pass
    return None


async def enviar_log_privado(bot, titulo: str, descricao: str, erro: bool = False):
    """Log privado — tudo: ganhou cargo, perdeu, clicou no botão."""
    try:
        config = carregar_config()
        canal = await _get_canal(bot, config.get("canal_logs_privado_id"))
        if not canal:
            return

        ph = _primary_hex()
        danger_hex = (db.get_document("custom_colors") or {}).get("danger", "#dc3545")
        cor_hex = danger_hex if erro else (ph or "#5865F2")
        cor = disnake.Colour(int(cor_hex.replace("#", ""), 16))

        if _mode() == "embed":
            emb = disnake.Embed(
                title=f"{emoji.wrong if erro else emoji.shield} {titulo}",
                description=descricao,
                color=cor,
            )
            await canal.send(embed=emb)
        else:
            kw = accent(ph)
            await canal.send(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"## {emoji.wrong if erro else emoji.shield} {titulo}\n{descricao}"
                    ),
                    **kw,
                )
            ])
    except Exception:
        pass


async def enviar_log_publico(bot, titulo: str, descricao: str):
    """Log público — apenas: perdeu cargo, clicou no botão (resultado)."""
    try:
        config = carregar_config()
        canal = await _get_canal(bot, config.get("canal_logs_publico_id"))
        if not canal:
            return

        ph = _primary_hex()
        cor = disnake.Colour(int((ph or "#5865F2").replace("#", ""), 16))

        if _mode() == "embed":
            emb = disnake.Embed(title=titulo, description=descricao, color=cor)
            await canal.send(embed=emb)
        else:
            kw = accent(ph)
            await canal.send(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"## {titulo}\n{descricao}"),
                    **kw,
                )
            ])
    except Exception:
        pass