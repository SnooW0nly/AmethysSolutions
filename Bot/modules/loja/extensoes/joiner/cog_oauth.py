"""
cog_oauth.py — Handler do callback OAuth2 integrado à API própria (Node.js)

O fluxo completo:
1. Usuário clica no botão de autorização → redirect para Discord OAuth2
2. Discord redireciona para: {api_url}/joiner/callback?code=...&state=...
3. A API Node.js processa o exchange diretamente (multi-tenant)
4. Bot recebe evento via WebSocket:
   - 'joiner_token_linked'  → OAuth2 vinculado a token de conta existente
   - 'joiner_oauth_cached'  → OAuth2 salvo em cache (sem token de conta disponível)
5. O boost é executado pelo JS API quando o gift é resgatado.
"""
from __future__ import annotations

import asyncio
import logging
import disnake
from disnake.ext import commands

from functions.emoji import emoji

from .helpers import (
    load_config, consume_oauth_state,
    save_member_token,
    cache_oauth_credentials,
    link_token_to_oauth, list_account_tokens,
    count_account_tokens, get_gift_stats, count_members,
    get_api_base_url,
)

logger = logging.getLogger(__name__)

_bot_ref = None


class JoinerOAuthCog(commands.Cog):
    """
    Registra callbacks no WebSocket da API própria (Node.js) para processar
    os eventos OAuth2 — salva tokens e notifica usuários via DM.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        global _bot_ref
        _bot_ref = bot
        self._register_ws_callbacks()

    def _register_ws_callbacks(self):
        try:
            from .websocket_manager import get_websocket_manager
            ws = get_websocket_manager()
            if ws is None:
                logger.warning("[Joiner OAuth] WebSocket manager não disponível ainda.")
                return

            @ws.on("joiner_token_linked")
            async def handle_token_linked(data):
                """Chamado quando o JS vincula um OAuth2 a um token de conta."""
                discord_user_id = data.get("discord_user_id")
                access_token    = data.get("access_token", "")
                refresh_token   = data.get("refresh_token", "")
                username        = data.get("username", "")
                expires_in      = data.get("expires_in", 604800)
                token_id        = data.get("token_id")

                if discord_user_id and access_token:
                    save_member_token(
                        discord_user_id=int(discord_user_id),
                        access_token=access_token,
                        refresh_token=refresh_token,
                        username=username,
                        expires_in=expires_in,
                    )
                    if token_id:
                        link_token_to_oauth(token_id, int(discord_user_id))

                    logger.info(f"[Joiner OAuth] 🔗 Token vinculado via JS: {username} ({discord_user_id})")

                    bot = _bot_ref
                    if bot:
                        try:
                            user = await bot.fetch_user(int(discord_user_id))
                            await user.send(
                                f"{emoji.correct} **Token vinculado!**\n"
                                "-# Sua conta foi vinculada com sucesso. Você será adicionado ao servidor quando um gift for resgatado."
                            )
                        except Exception:
                            pass

            @ws.on("joiner_oauth_cached")
            async def handle_oauth_cached(data):
                """Chamado quando o OAuth2 é salvo em cache (sem token disponível)."""
                discord_user_id = data.get("discord_user_id")
                access_token    = data.get("access_token", "")
                refresh_token   = data.get("refresh_token", "")
                username        = data.get("username", "")
                expires_in      = data.get("expires_in", 604800)

                if discord_user_id and access_token:
                    cache_oauth_credentials(
                        discord_user_id=int(discord_user_id),
                        username=username,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_in=expires_in,
                    )
                    logger.info(f"[Joiner OAuth] ⏳ OAuth em cache via JS: {username} ({discord_user_id})")

                    bot = _bot_ref
                    if bot:
                        try:
                            user = await bot.fetch_user(int(discord_user_id))
                            await user.send(
                                f"{emoji.correct} **Autorização recebida!**\n"
                                "-# Sua conta está em fila. Você será adicionado ao servidor assim que um token for disponibilizado."
                            )
                        except Exception:
                            pass

            # Fallback legado: o bot Python pode ainda receber o code/state diretamente
            # (para bots sem credenciais registradas no JS)
            @ws.on("joiner_oauth_callback")
            async def handle_oauth_legacy(data):
                code  = data.get("code", "")
                state = data.get("state", "")
                if code and state:
                    asyncio.create_task(self._handle_oauth_legacy(code, state))

            logger.info("[Joiner OAuth] Callbacks registrados no WebSocket.")

        except Exception as e:
            logger.error(f"[Joiner OAuth] Erro ao registrar callbacks: {e}")

    async def _handle_oauth_legacy(self, code: str, state: str):
        """Fallback: processa OAuth2 diretamente no Python (para bots sem creds no JS)."""
        import aiohttp

        cfg = load_config()
        state_data = consume_oauth_state(state)
        if not state_data:
            logger.warning("[Joiner OAuth][legacy] State inválido ou expirado.")
            return

        data = {
            "client_id":     cfg.get("oauth_client_id", ""),
            "client_secret": cfg.get("oauth_client_secret", ""),
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  f"{get_api_base_url()}{cfg.get('callback_path', '/joiner/callback')}",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://discord.com/api/v10/oauth2/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"[Joiner OAuth][legacy] Exchange falhou: {resp.status}")
                        return
                    token_data = await resp.json()

                async with session.get(
                    "https://discord.com/api/v10/users/@me",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status != 200:
                        return
                    user_info = await resp.json()

            discord_user_id = int(user_info.get("id", 0))
            username = user_info.get("username", "Unknown")

            save_member_token(
                discord_user_id=discord_user_id,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", ""),
                username=username,
                expires_in=token_data.get("expires_in", 604800),
            )

            logger.info(f"[Joiner OAuth][legacy] ✅ Token salvo: {username} ({discord_user_id})")

            bot = _bot_ref
            if bot:
                try:
                    user = await bot.fetch_user(discord_user_id)
                    await user.send(
                        f"{emoji.correct} **Autorização concluída!**\n"
                        "-# Sua conta foi autorizada com sucesso."
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"[Joiner OAuth][legacy] Erro: {e}")
