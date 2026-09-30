from disnake.ext import tasks
import asyncio
import core

_bot_instance = None

@tasks.loop(minutes=1)
async def change_bio_task(bot):
    global _bot_instance
    _bot_instance = bot
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, core.change_bio)
    except Exception as e:
        print(f"Erro ao atualizar bio: {e}")

@change_bio_task.before_loop
async def before_change_bio_task():
    if _bot_instance:
        await _bot_instance.wait_until_ready()