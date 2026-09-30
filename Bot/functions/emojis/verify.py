import aiohttp
import asyncio
import os
import json

# Cooldown mínimo entre requisições
REQUEST_COOLDOWN = 0.3


def verify_emoji(app_id: str, bot_token: str, emoji_id: str) -> bool:
    """Versão síncrona para compatibilidade"""
    return asyncio.run(verify_emoji_async(app_id, bot_token, emoji_id))


async def verify_emoji_async(app_id: str, bot_token: str, emoji_id: str) -> bool:
    # Carregar configs/config_emoji.json
    config_emoji_path = "configs/config_emoji.json"
    config_emoji = {}

    if os.path.exists(config_emoji_path):
        with open(config_emoji_path, "r", encoding="utf-8") as f:
            config_emoji = json.load(f)

    is_configured = config_emoji.get("isConfigured", False)

    # Se isConfigured for true, não verificar
    if is_configured:
        print(
            f"[EmojiVerify] Emoji ID '{emoji_id}' - verificação pulada (isConfigured=true)"
        )
        return True

    # Se isConfigured for false, verificar os outros requisitos
    # Carregar emojis_data.json
    emojis_data_path = "database/emojis/emojis_data.json"
    emojis_data = {}

    if os.path.exists(emojis_data_path):
        with open(emojis_data_path, "r", encoding="utf-8") as f:
            emojis_data = json.load(f)

    configured = emojis_data.get("configured", "false")
    last_token = emojis_data.get("lastToken", "")

    # Verificar apenas se: configured for diferente de "True" OU token for diferente
    should_verify = configured != "True" or (last_token and last_token != bot_token)

    if not should_verify:
        # Se não precisa verificar, assumir que o emoji existe
        print(
            f"[EmojiVerify] Emoji ID '{emoji_id}' - verificação pulada (já configurado com mesmo token)"
        )
        return True

    # Fazer verificação na API do Discord
    url = f"https://discord.com/api/v10/applications/{app_id}/emojis/{emoji_id}"
    headers = {"Authorization": f"Bot {bot_token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                print(f"[EmojiVerify] Emoji ID '{emoji_id}' verificado com sucesso!")
                return True
            else:
                print(
                    f"[EmojiVerify] Emoji ID '{emoji_id}' não encontrado ou inválido. Status: {resp.status}"
                )
                return False


async def verify_emojis_batch(
    app_id: str, bot_token: str, emoji_ids: list, max_concurrent: int = 20
) -> dict:
    """
    Verifica múltiplos emojis em paralelo
    Retorna um dicionário {emoji_id: bool}
    """
    # Verificar configurações uma vez
    config_emoji_path = "configs/config_emoji.json"
    config_emoji = {}

    if os.path.exists(config_emoji_path):
        with open(config_emoji_path, "r", encoding="utf-8") as f:
            config_emoji = json.load(f)

    is_configured = config_emoji.get("isConfigured", False)

    if is_configured:
        print(
            f"[EmojiVerify] Verificação pulada para todos os {len(emoji_ids)} emojis (isConfigured=true)"
        )
        return {emoji_id: True for emoji_id in emoji_ids}

    emojis_data_path = "database/emojis/emojis_data.json"
    emojis_data = {}

    if os.path.exists(emojis_data_path):
        with open(emojis_data_path, "r", encoding="utf-8") as f:
            emojis_data = json.load(f)

    configured = emojis_data.get("configured", "false")
    last_token = emojis_data.get("lastToken", "")

    should_verify = configured != "True" or (last_token and last_token != bot_token)

    if not should_verify:
        print(
            f"[EmojiVerify] Verificação pulada para todos os {len(emoji_ids)} emojis (já configurado)"
        )
        return {emoji_id: True for emoji_id in emoji_ids}

    # Verificar em paralelo
    connector = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i, emoji_id in enumerate(emoji_ids):
            # Aplicar cooldown antes de cada task
            if i > 0:
                await asyncio.sleep(REQUEST_COOLDOWN)
            task = _verify_single_emoji(session, app_id, bot_token, emoji_id)
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)

    return dict(zip(emoji_ids, results))


async def _verify_single_emoji(
    session: aiohttp.ClientSession, app_id: str, bot_token: str, emoji_id: str
) -> bool:
    """Função auxiliar para verificar um único emoji"""
    url = f"https://discord.com/api/v10/applications/{app_id}/emojis/{emoji_id}"
    headers = {"Authorization": f"Bot {bot_token}"}

    try:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                print(f"[EmojiVerify] ✓ Emoji ID '{emoji_id}' verificado")
                return True
            else:
                print(f"[EmojiVerify] ✗ Emoji ID '{emoji_id}' inválido ({resp.status})")
                return False
    except Exception as e:
        print(f"[EmojiVerify] ✗ Erro ao verificar emoji '{emoji_id}': {e}")
        return False