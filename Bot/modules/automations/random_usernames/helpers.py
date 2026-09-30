"""
modules/automations/random_usernames/helpers.py

Helpers de configuração e persistência para o módulo Random Usernames.

Toggles disponíveis:
  - toggle_3l  → habilita escaneamento de usernames com 3 letras
  - toggle_4l  → habilita escaneamento de usernames com 4 letras
  - toggle_rep → habilita geração com chars repetidos consecutivos
                 (ex: "aaaa", "7d7d", "kkkk")
  2l é sempre escaneado quando o sistema está ativo — sem toggle.

Canais: um por comprimento (2l, 3l, 4l). Cada comprimento tem seu canal
individual configurado via select menu dos canais do servidor.
"""
from __future__ import annotations

from functions.database import database as db
from functions.emoji import emoji

_DB_KEY = "random_usernames_config"

_DEFAULT: dict = {
    "ativado":    False,
    "toggle_3l":  False,   # escaneamento de 3 letras OFF por padrão
    "toggle_4l":  False,   # escaneamento de 4 letras OFF por padrão
    "toggle_rep": False,   # repeat OFF por padrão
    "canal_2l":   None,
    "canal_3l":   None,
    "canal_4l":   None,
}


# ══════════════════════════════════════════════════════════════════════════════
# Normalização
# ══════════════════════════════════════════════════════════════════════════════

def _normalizar_canal(valor) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    return s if s.isdigit() else None


def _merge(raw: dict) -> dict:
    cfg = {**_DEFAULT, **(raw if isinstance(raw, dict) else {})}
    cfg["ativado"]    = bool(cfg.get("ativado",    False))
    cfg["toggle_3l"]  = bool(cfg.get("toggle_3l",  False))
    cfg["toggle_4l"]  = bool(cfg.get("toggle_4l",  False))
    cfg["toggle_rep"] = bool(cfg.get("toggle_rep", False))
    cfg["canal_2l"]   = _normalizar_canal(cfg.get("canal_2l"))
    cfg["canal_3l"]   = _normalizar_canal(cfg.get("canal_3l"))
    cfg["canal_4l"]   = _normalizar_canal(cfg.get("canal_4l"))
    return cfg


# ══════════════════════════════════════════════════════════════════════════════
# CRUD
# ══════════════════════════════════════════════════════════════════════════════

def ler_config() -> dict:
    raw = db.get_document(_DB_KEY) or {}
    return _merge(raw)


def salvar_config(cfg: dict) -> dict:
    safe = _merge(cfg)
    db.save_document(_DB_KEY, {}, safe)
    return safe


def atualizar_config(updater) -> dict:
    atual = ler_config()
    proximo = updater(atual)
    return salvar_config(proximo or atual)


# ══════════════════════════════════════════════════════════════════════════════
# Toggles
# ══════════════════════════════════════════════════════════════════════════════

def toggle_campo(campo: str) -> bool:
    novo: dict = {"estado": None}

    def up(cfg):
        cfg[campo] = not bool(cfg.get(campo, False))
        novo["estado"] = cfg[campo]
        return cfg

    atualizar_config(up)
    return novo["estado"]  # type: ignore[return-value]


def set_ativado(valor: bool) -> dict:
    def up(cfg):
        cfg["ativado"] = bool(valor)
        return cfg
    return atualizar_config(up)


# ══════════════════════════════════════════════════════════════════════════════
# Canais por comprimento
# ══════════════════════════════════════════════════════════════════════════════

def set_canal(comp: str, channel_id: str | None) -> dict:
    """comp: '2l', '3l' ou '4l'"""
    campo = f"canal_{comp}"

    def up(cfg):
        cfg[campo] = _normalizar_canal(channel_id)
        return cfg

    return atualizar_config(up)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de leitura
# ══════════════════════════════════════════════════════════════════════════════

def comprimentos_ativos(cfg: dict) -> list[int]:
    """
    Retorna os comprimentos (int) que devem ser escaneados.
    2l é sempre incluído. 3l e 4l dependem dos toggles.
    """
    ativos = [2]
    if cfg.get("toggle_3l"):
        ativos.append(3)
    if cfg.get("toggle_4l"):
        ativos.append(4)
    return ativos


def canais_por_comprimento(cfg: dict) -> dict[int, str | None]:
    return {
        2: cfg.get("canal_2l"),
        3: cfg.get("canal_3l"),
        4: cfg.get("canal_4l"),
    }


def tem_canal_minimo(cfg: dict) -> bool:
    """True se ao menos o canal do 2l estiver configurado."""
    return bool(cfg.get("canal_2l"))


def _fmt_canal(cid: str | None) -> str:
    return f"<#{cid}>" if cid else "`Não configurado`"


def resumo(cfg: dict) -> str:
    status = f"{emoji.on} **Ativo**" if cfg["ativado"] else f"{emoji.off} **Inativo**"

    comp_parts = ["2l (fixo)"]
    if cfg["toggle_3l"]:
        comp_parts.append("3l")
    if cfg["toggle_4l"]:
        comp_parts.append("4l")

    repeat_desc = (
        "Ativo — permite chars repetidos consecutivos (ex: `aaaa`, `7d7d`)"
        if cfg["toggle_rep"]
        else "Inativo"
    )

    return (
        f"**Status:** {status}\n"
        f"**Comprimentos:** `{'  |  '.join(comp_parts)}`\n"
        f"**Repeat:** {repeat_desc}\n"
        f"**Canal 2l:** {_fmt_canal(cfg.get('canal_2l'))}\n"
        f"**Canal 3l:** {_fmt_canal(cfg.get('canal_3l'))}\n"
        f"**Canal 4l:** {_fmt_canal(cfg.get('canal_4l'))}"
    )