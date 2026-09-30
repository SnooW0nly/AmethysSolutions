import os
import base64
import aiohttp
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Cooldown mínimo entre requisições
REQUEST_COOLDOWN = 0.3

async def upload_emoji_async(session, name, image_path, app_id, bot_token):
    ext = os.path.splitext(image_path)[1].lower()
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()

    tipo = "gif" if ext == ".gif" else "png"
    base64_image = f"data:image/{tipo};base64,{base64.b64encode(image_data).decode()}"

    url = f"https://discord.com/api/v10/applications/{app_id}/emojis"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "image": base64_image
    }

    async with session.post(url, headers=headers, json=payload) as response:
        if response.status == 201:
            data = await response.json()
            emoji_id = data["id"]
            print(f"[EmojiUpload] Emoji '{name}' adicionado com sucesso! ID: {emoji_id}")
            return emoji_id
        else:
            text = await response.text()
            print(f"[EmojiUpload] Erro ao criar emoji '{name}': {response.status} - {text}")
            raise Exception(f"Erro ao criar emoji {name}: {response.status} - {text}")

def upload_emoji(name, image_path, app_id, bot_token):
    """Versão síncrona para compatibilidade"""
    return asyncio.run(upload_emoji_async_wrapper(name, image_path, app_id, bot_token))

async def upload_emoji_async_wrapper(name, image_path, app_id, bot_token):
    async with aiohttp.ClientSession() as session:
        return await upload_emoji_async(session, name, image_path, app_id, bot_token)

async def upload_emojis_batch(emojis_data, app_id, bot_token, max_concurrent=5):
    """
    Upload múltiplos emojis em paralelo
    emojis_data: lista de tuplas (name, image_path)
    max_concurrent: número máximo de uploads simultâneos
    """
    connector = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i, (name, image_path) in enumerate(emojis_data):
            # Aplicar cooldown antes de cada task
            if i > 0:
                await asyncio.sleep(REQUEST_COOLDOWN)
            task = asyncio.create_task(upload_emoji_async(session, name, image_path, app_id, bot_token))
            tasks.append(task)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results