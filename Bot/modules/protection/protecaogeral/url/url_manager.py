import aiohttp
from typing import Optional, Tuple
from functions.database import database as db

DISCORD_API_BASE = "https://discord.com/api/v10"

class URLManager:
    def __init__(self, bot):
        self.bot = bot

    def _get_token_data(self, user_id: str) -> Optional[dict]:
        tokens = db.get_document("tokens", {}).get("list", [])
        return next((t for t in tokens if t["user_id"] == user_id), None)

    async def get_current_vanity_code(self, guild_id: int, token: str) -> Optional[str]:
        """Obtém o código de vanity URL atual do servidor."""
        headers = {"Authorization": token}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DISCORD_API_BASE}/guilds/{guild_id}", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("vanity_url_code")
                return None

    async def set_vanity_url(self, guild_id: int, token: str, password: str, code: str) -> Tuple[bool, str]:
        """
        Define a vanity URL do servidor.
        Requer envio da senha no header X-Discord-Password.
        Retorna (sucesso, mensagem).
        """
        headers = {
            "Authorization": token,
            "Content-Type": "application/json",
            "X-Discord-Password": password,
        }
        payload = {"code": code}
        async with aiohttp.ClientSession() as session:
            async with session.patch(f"{DISCORD_API_BASE}/guilds/{guild_id}", headers=headers, json=payload) as resp:
                if resp.status == 200:
                    return True, "URL configurada com sucesso!"
                elif resp.status == 400:
                    text = await resp.text()
                    if "invalid vanity code" in text.lower():
                        return False, "Código inválido. Use apenas letras, números e traços."
                    return False, f"Erro 400: {text}"
                elif resp.status == 401:
                    return False, "Token inválido ou expirado."
                elif resp.status == 403:
                    text = await resp.text()
                    if "password" in text.lower():
                        return False, "Senha incorreta ou conta com 2FA ativo. A proteção de URL exige conta sem 2FA."
                    return False, "Sem permissão para alterar a URL. A conta precisa ter permissão `MANAGE_GUILD`."
                elif resp.status == 429:
                    return False, "Muitas tentativas. Aguarde e tente novamente."
                else:
                    return False, f"Erro {resp.status}: {await resp.text()}"

    async def refresh_vanity(self, guild_id: int, user_id: str, target_code: str) -> Tuple[bool, str]:
        """Tenta restaurar a vanity URL caso tenha sido alterada."""
        token_data = self._get_token_data(user_id)
        if not token_data:
            return False, "Conta de token não encontrada."
        current = await self.get_current_vanity_code(guild_id, token_data["token"])
        if current != target_code:
            return await self.set_vanity_url(guild_id, token_data["token"],
                                              token_data.get("password", ""), target_code)
        return True, "URL já está correta."