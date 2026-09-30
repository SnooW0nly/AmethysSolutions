"""
modules/loja/marketplace/reseller.py
─────────────────────────────────────
Lógica de revenda: parar revenda, notificações ao dono do produto e cooldown.

Funções públicas:
  - notify_owner_start(bot, product, reseller, guild, channel_id)
      Notifica o dono do bot-produto que alguém começou a revender.

  - stop_and_notify(bot, user_id, select_value, reseller)
      Para a revenda, aplica cooldown e notifica o dono que ela foi encerrada.
      Retorna o dict do registro removido ou None se não encontrado.

NOTAS DE I/O
─────────────
As chamadas HTTP à API da plataforma agora usam httpx.AsyncClient, que é
totalmente assíncrono e não bloqueia o event loop.  A biblioteca `requests`
era síncrona e, com timeout=10, podia paralisar o event loop por até 10 s
durante interações do usuário.
"""

from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.marketplace import ResaleProduct, stop_resale


# ──────────────────────────────────────────────────────────────────────────────
#  Helpers internos
# ──────────────────────────────────────────────────────────────────────────────

def _reseller_embed(
    title: str,
    description: str,
    color: disnake.Colour = disnake.Colour.blurple(),
) -> disnake.Embed:
    return disnake.Embed(title=title, description=description, color=color)


async def _try_dm(bot: disnake.Client, user_id: int, **kwargs) -> bool:
    """Tenta enviar DM ao usuário. Retorna True se bem-sucedido."""
    try:
        user = bot.get_user(user_id) or await bot.fetch_user(user_id)
        await user.send(**kwargs)
        return True
    except Exception:
        return False


async def _fetch_bot_owner_id(api_url: str, bot_token: str, bot_id: str) -> int | None:
    """
    Busca o Discord user ID do dono de um bot via API da plataforma.

    GET {api_url}/api/bot/{bot_id}/info → { "owner": "<user_id>" }

    Usa httpx.AsyncClient para não bloquear o event loop.
    Faz fallback silencioso para requests (síncrono via asyncio.to_thread)
    caso httpx não esteja instalado.
    """
    url = f"{api_url}/api/bot/{bot_id}/info"
    headers = {"authorization": bot_token, "content-type": "application/json"}

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            return int(resp.json().get("owner", 0)) or None
    except ImportError:
        # httpx não instalado — fallback síncrono em thread separada
        import asyncio
        import requests as _requests

        def _sync_get() -> int | None:
            try:
                r = _requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200:
                    return int(r.json().get("owner", 0)) or None
            except Exception:
                pass
            return None

        return await asyncio.to_thread(_sync_get)
    except Exception as e:
        print(f"[Marketplace] Erro ao buscar owner do bot '{bot_id}': {e}")

    return None


def _load_api_config() -> tuple[str, str]:
    """Retorna (api_url, bot_token) do config.json. Strings vazias se ausentes."""
    from functions.database import database as db
    config = db.obter("config.json")
    return config.get("apiURL", "").rstrip("/"), config.get("botToken", "")


# ──────────────────────────────────────────────────────────────────────────────
#  Notificação ao dono: início de revenda
# ──────────────────────────────────────────────────────────────────────────────

async def notify_owner_start(
    bot: disnake.Client,
    product: ResaleProduct,
    reseller: disnake.Member | disnake.User,
    guild: disnake.Guild | None,
    channel_id: str | int,
) -> None:
    """
    Notifica o dono do bot-produto via DM quando alguém começa a revender.

    Busca o Discord user ID do dono via API da plataforma:
        GET {apiURL}/api/bot/{owner_bot_id}/info → response.owner
    """
    api_url, bot_token = _load_api_config()

    if not api_url or not bot_token or not product.bot_id:
        print(f"[Marketplace] Config incompleta — DM de início de revenda não enviada.")
        return

    owner_id = await _fetch_bot_owner_id(api_url, bot_token, product.bot_id)

    if not owner_id:
        print(f"[Marketplace] Não foi possível identificar o dono do bot '{product.bot_id}' — DM não enviada.")
        return

    guild_name = guild.name if guild else "Servidor desconhecido"
    guild_id   = guild.id   if guild else "?"

    embed = _reseller_embed(
        title=f"{emoji.basket} Nova Revenda Iniciada",
        description=(
            f"**{reseller}** (`{reseller.id}`) começou a revender seu produto.\n\n"
            f"**Produto:** {product.name}\n"
            f"**Servidor:** {guild_name} (`{guild_id}`)\n"
            f"**Canal:** <#{channel_id}>\n\n"
            f"-# Comissão configurada: {product.commission_label}"
        ),
        color=disnake.Colour.green(),
    )

    await _try_dm(bot, owner_id, embed=embed)


# ──────────────────────────────────────────────────────────────────────────────
#  Parar revenda + notificação ao dono
# ──────────────────────────────────────────────────────────────────────────────

async def stop_and_notify(
    bot: disnake.Client,
    user_id: str,
    select_value: str,
    reseller: disnake.Member | disnake.User,
) -> dict | None:
    """
    Para a revenda do `select_value` pelo usuário `user_id`,
    aplica cooldown de 30 min e notifica o dono do produto via DM.

    Retorna o registro removido (dict) ou None se não encontrado.
    """
    entry = stop_resale(user_id, select_value)
    if entry is None:
        return None

    product_name = entry.get("product_name", "Produto desconhecido")
    guild_name   = entry.get("guild_name",   "Servidor desconhecido")
    guild_id     = entry.get("guild_id",     "?")
    channel_id   = entry.get("channel_id",   "?")
    bot_id_raw   = entry.get("bot_id",       "")

    embed = _reseller_embed(
        title=f"{emoji.alert} Revenda Encerrada",
        description=(
            f"**{reseller}** (`{reseller.id}`) parou de revender seu produto.\n\n"
            f"**Produto:** {product_name}\n"
            f"**Servidor:** {guild_name} (`{guild_id}`)\n"
            f"**Canal:** <#{channel_id}>\n\n"
            f"-# O painel no canal pode ter sido removido pelo revendedor.\n"
            f"-# O usuário ficará em cooldown de **30 minutos** para revendê-lo novamente."
        ),
        color=disnake.Colour.red(),
    )

    if not bot_id_raw:
        print("[Marketplace] bot_id ausente no registro de revenda — DM de encerramento não enviada.")
        return entry

    api_url, bot_token = _load_api_config()
    if not api_url or not bot_token:
        print("[Marketplace] Config incompleta — DM de encerramento não enviada.")
        return entry

    owner_id = await _fetch_bot_owner_id(api_url, bot_token, bot_id_raw)

    if owner_id:
        await _try_dm(bot, owner_id, embed=embed)
    else:
        print(f"[Marketplace] Não foi possível identificar o dono do bot '{bot_id_raw}' — DM não enviada.")

    return entry


# ──────────────────────────────────────────────────────────────────────────────
#  Cog de setup (sem listeners próprios; lógica fica no cog.py)
# ──────────────────────────────────────────────────────────────────────────────

def setup(bot: commands.Bot) -> None:
    pass  # Sem cog próprio — funções são chamadas diretamente pelo MarketplaceCog