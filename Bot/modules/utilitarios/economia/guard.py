"""
modules/utilitarios/economia/guard.py

Sistema de proteção dos comandos de economia.
Verificações: blacklist (usuário/cargo) → canal → ratelimit global.

Uso em qualquer comando de prefixo:
    from ..guard import EconomyGuard

    allowed, reason = EconomyGuard.check(ctx)
    if not allowed:
        await ctx.reply(reason, delete_after=6)
        return
"""

from __future__ import annotations

import time
from typing import Optional

from disnake.ext import commands

from functions.emoji import emoji
from .helper import EconomyHelper


# Cache em memória: user_id → timestamp monotônico do último comando
_rl_cache: dict[int, float] = {}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ─────────────────────────────────────────────────────────────────────────────

def _get_guard() -> dict:
    return EconomyHelper.get_economy_settings().get("guard", {})


def _save_guard(guard: dict):
    s = EconomyHelper.get_economy_settings()
    s["guard"] = guard
    EconomyHelper.save_economy_settings(s)


# ─────────────────────────────────────────────────────────────────────────────
# CLASSE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class EconomyGuard:

    # ══════════════════════════════════════════════════════════════════════════
    # CHECK UNIFICADO
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def check(ctx: commands.Context) -> tuple[bool, Optional[str]]:
        """
        Verifica em ordem:
          1. Blacklist de usuário
          2. Blacklist de cargo
          3. Canal bloqueado
          4. Canal fora da lista de permitidos (quando lista existe)
          5. Ratelimit (cargos bypass ignoram)

        Retorna (True, None) se liberado, ou (False, "mensagem") se bloqueado.
        """
        guard    = _get_guard()
        member   = ctx.author
        user_id  = ctx.author.id
        chan_id  = ctx.channel.id
        role_ids = {r.id for r in getattr(member, "roles", [])}

        # 1. Blacklist de usuário
        bl = guard.get("blacklist", {})
        if user_id in bl.get("users", []):
            return False, f"{emoji.wrong} Você está na blacklist e não pode usar comandos de economia."

        # 2. Blacklist de cargo
        if role_ids & set(bl.get("roles", [])):
            return False, f"{emoji.wrong} Um dos seus cargos está bloqueado para usar comandos de economia."

        # 3. Canal bloqueado
        ch = guard.get("channels", {})
        if chan_id in ch.get("blocked", []):
            return False, f"{emoji.wrong} Comandos de economia não são permitidos neste canal."

        # 4. Canal não está na lista de permitidos (quando lista existe)
        allowed = ch.get("allowed", [])
        if allowed and chan_id not in allowed:
            mentions = " ".join(f"<#{c}>" for c in allowed[:5])
            return False, f"{emoji.wrong} Use os comandos de economia em: {mentions}"

        # 5. Ratelimit
        rl = guard.get("ratelimit", {})
        if rl.get("enabled", False):
            seconds      = float(rl.get("seconds", 2))
            bypass_roles = set(rl.get("bypass_roles", []))
            if not (role_ids & bypass_roles):
                last      = _rl_cache.get(user_id, 0.0)
                now       = time.monotonic()
                remaining = seconds - (now - last)
                if remaining > 0:
                    s = f"{remaining:.1f}".rstrip("0").rstrip(".")
                    return False, f"{emoji.wrong} Aguarde **{s}s** antes de usar outro comando."
                _rl_cache[user_id] = now
            else:
                _rl_cache[user_id] = time.monotonic()
        else:
            _rl_cache[user_id] = time.monotonic()

        return True, None

    # ══════════════════════════════════════════════════════════════════════════
    # RATELIMIT
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def get_ratelimit() -> dict:
        return _get_guard().get("ratelimit", {"enabled": False, "seconds": 2.0, "bypass_roles": []})

    @staticmethod
    def set_ratelimit_enabled(enabled: bool):
        g = _get_guard()
        g.setdefault("ratelimit", {"enabled": False, "seconds": 2.0, "bypass_roles": []})["enabled"] = enabled
        _save_guard(g)

    @staticmethod
    def set_ratelimit_seconds(seconds: float):
        g = _get_guard()
        g.setdefault("ratelimit", {"enabled": False, "seconds": 2.0, "bypass_roles": []})["seconds"] = max(0.5, float(seconds))
        _save_guard(g)

    @staticmethod
    def add_bypass_role(role_id: int):
        g  = _get_guard()
        rl = g.setdefault("ratelimit", {"enabled": False, "seconds": 2.0, "bypass_roles": []})
        if role_id not in rl.setdefault("bypass_roles", []):
            rl["bypass_roles"].append(role_id)
        _save_guard(g)

    @staticmethod
    def remove_bypass_role(role_id: int):
        g  = _get_guard()
        rl = g.get("ratelimit", {})
        rl["bypass_roles"] = [r for r in rl.get("bypass_roles", []) if r != role_id]
        g["ratelimit"] = rl
        _save_guard(g)

    # ══════════════════════════════════════════════════════════════════════════
    # BLACKLIST
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def get_blacklist() -> dict:
        return _get_guard().get("blacklist", {"users": [], "roles": []})

    @staticmethod
    def blacklist_add_user(user_id: int):
        g  = _get_guard()
        bl = g.setdefault("blacklist", {"users": [], "roles": []})
        if user_id not in bl.setdefault("users", []):
            bl["users"].append(user_id)
        _save_guard(g)

    @staticmethod
    def blacklist_remove_user(user_id: int):
        g  = _get_guard()
        bl = g.get("blacklist", {})
        bl["users"] = [u for u in bl.get("users", []) if u != user_id]
        g["blacklist"] = bl
        _save_guard(g)

    @staticmethod
    def blacklist_add_role(role_id: int):
        g  = _get_guard()
        bl = g.setdefault("blacklist", {"users": [], "roles": []})
        if role_id not in bl.setdefault("roles", []):
            bl["roles"].append(role_id)
        _save_guard(g)

    @staticmethod
    def blacklist_remove_role(role_id: int):
        g  = _get_guard()
        bl = g.get("blacklist", {})
        bl["roles"] = [r for r in bl.get("roles", []) if r != role_id]
        g["blacklist"] = bl
        _save_guard(g)

    @staticmethod
    def blacklist_clear_users():
        g = _get_guard()
        g.setdefault("blacklist", {})["users"] = []
        _save_guard(g)

    @staticmethod
    def blacklist_clear_roles():
        g = _get_guard()
        g.setdefault("blacklist", {})["roles"] = []
        _save_guard(g)

    # ══════════════════════════════════════════════════════════════════════════
    # CANAIS
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def get_channels() -> dict:
        return _get_guard().get("channels", {"allowed": [], "blocked": []})

    @staticmethod
    def channel_allow(channel_id: int):
        g  = _get_guard()
        ch = g.setdefault("channels", {"allowed": [], "blocked": []})
        if channel_id not in ch.setdefault("allowed", []):
            ch["allowed"].append(channel_id)
        ch["blocked"] = [c for c in ch.get("blocked", []) if c != channel_id]
        _save_guard(g)

    @staticmethod
    def channel_unallow(channel_id: int):
        g  = _get_guard()
        ch = g.get("channels", {})
        ch["allowed"] = [c for c in ch.get("allowed", []) if c != channel_id]
        g["channels"] = ch
        _save_guard(g)

    @staticmethod
    def channel_block(channel_id: int):
        g  = _get_guard()
        ch = g.setdefault("channels", {"allowed": [], "blocked": []})
        if channel_id not in ch.setdefault("blocked", []):
            ch["blocked"].append(channel_id)
        ch["allowed"] = [c for c in ch.get("allowed", []) if c != channel_id]
        _save_guard(g)

    @staticmethod
    def channel_unblock(channel_id: int):
        g  = _get_guard()
        ch = g.get("channels", {})
        ch["blocked"] = [c for c in ch.get("blocked", []) if c != channel_id]
        g["channels"] = ch
        _save_guard(g)

    @staticmethod
    def channels_clear_allowed():
        g = _get_guard()
        g.setdefault("channels", {})["allowed"] = []
        _save_guard(g)

    @staticmethod
    def channels_clear_blocked():
        g = _get_guard()
        g.setdefault("channels", {})["blocked"] = []
        _save_guard(g)

    # ══════════════════════════════════════════════════════════════════════════
    # UTILITÁRIOS
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def clear_rl_cache():
        """Limpa o cache em memória do ratelimit (útil em reloads)."""
        _rl_cache.clear()
