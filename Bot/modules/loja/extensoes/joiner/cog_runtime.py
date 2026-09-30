"""
cog_runtime.py — Motor de execução: botão público e slash command
Processa a solicitação do usuário e inicia o fluxo OAuth2.

IMPORTANTE: Após o OAuth, o token é apenas salvo — nenhum servidor é adicionado aqui.
A adição ao servidor e o boost acontecem via Gift (JS API).
"""
from __future__ import annotations

import disnake
from disnake.ext import commands
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji

from .helpers import (
    load_config,
    create_oauth_state,
    get_api_base_url,
)


def _get_oauth_url(cfg: dict, state: str) -> Optional[str]:
    client_id = cfg.get("oauth_client_id", "")
    if not client_id:
        return None
    api_url = get_api_base_url()
    callback = f"{api_url}{cfg.get('callback_path', '/joiner/callback')}"
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={callback}"
        f"&response_type=code"
        f"&scope=identify%20guilds.join"
        f"&state={state}"
        f"&prompt=none"
    )


def _accent() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


async def send_ephemeral_or_dm(
    inter: Optional[disnake.Interaction],
    user: disnake.User,
    content: str,
):
    if inter and not inter.response.is_done():
        try:
            await inter.response.send_message(content, ephemeral=True)
            return
        except Exception:
            pass
    if inter and inter.response.is_done():
        try:
            await inter.followup.send(content, ephemeral=True)
            return
        except Exception:
            pass
    try:
        await user.send(content)
    except Exception:
        pass


async def _handle_join_request(inter: disnake.Interaction, user: disnake.User):
    """
    Fluxo principal:
    1. Gera URL OAuth2 com state
    2. Envia botão de autorização ao usuário (components_v2)
    """
    cfg = load_config()

    if not cfg.get("enabled"):
        await send_ephemeral_or_dm(inter, user,
                                   f"{emoji.wrong} O sistema de entrada está desativado no momento.")
        return

    if not cfg.get("oauth_client_id") or not cfg.get("oauth_client_secret"):
        await send_ephemeral_or_dm(inter, user,
                                   f"{emoji.wrong} Sistema não configurado. Contate um administrador.")
        return

    state = create_oauth_state(user_id=user.id, key=None)
    oauth_url = _get_oauth_url(cfg, state)
    if not oauth_url:
        await send_ephemeral_or_dm(inter, user,
                                   f"{emoji.wrong} Client ID não configurado. Contate um administrador.")
        return

    tip_text = (
        f"Clique no botão abaixo para **autorizar** o acesso.\n"
        f"-# Ao autorizar, seu token será salvo e você será adicionado ao servidor quando um Gift for resgatado.\n"
        f"-# Permissão concedida: `guilds.join` (entrar em servidores em seu nome)."
    )

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"## 🔑 Autorização Necessária\n{tip_text}"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Autorizar", style=disnake.ButtonStyle.link,
                              url=oauth_url, emoji="🔑")
        ),
        **_accent(),
    )

    kwargs = dict(
        components=[container],
        flags=disnake.MessageFlags(is_components_v2=True),
        ephemeral=True,
    )

    if inter and not inter.response.is_done():
        await inter.response.send_message(**kwargs)
    elif inter:
        await inter.followup.send(**kwargs)
    else:
        try:
            await user.send(**kwargs)
        except Exception:
            pass


class JoinerRuntimeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""
        if cid == "Joiner_PublicEntrar":
            await _handle_join_request(inter, inter.user)
