import aiohttp
import asyncio

# Cooldown mínimo entre requisições
REQUEST_COOLDOWN = 0.3


async def delete_emoji_async(
    session: aiohttp.ClientSession, app_id: str, bot_token: str, emoji_id: str
) -> bool:
    url = f"https://discord.com/api/v10/applications/{app_id}/emojis/{emoji_id}"
    headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}

    async with session.delete(url, headers=headers) as response:
        if response.status == 204:
            print(f"[EmojiDelete] Emoji ID '{emoji_id}' deletado com sucesso!")
            return True
        elif response.status == 404:
            print(
                f"[EmojiDelete] Emoji ID '{emoji_id}' não encontrado (já foi deletado ou não existe)"
            )
            return False
        else:
            text = await response.text()
            print(
                f"[EmojiDelete] Erro ao deletar emoji ID '{emoji_id}'. Status: {response.status} - {text}"
            )
            return False


def delete_emoji(app_id: str, bot_token: str, emoji_id: str) -> bool:
    """Versão síncrona para compatibilidade"""
    return asyncio.run(delete_emoji_wrapper(app_id, bot_token, emoji_id))


async def delete_emoji_wrapper(app_id: str, bot_token: str, emoji_id: str) -> bool:
    async with aiohttp.ClientSession() as session:
        return await delete_emoji_async(session, app_id, bot_token, emoji_id)