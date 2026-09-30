from functions.database import database as db
from disnake.ext import tasks
import disnake
import itertools

# ── Tipos de presença (bolinha colorida) ──────────────────────────────────────
# "online"   → verde  | "idle"      → amarelo
# "dnd"      → vermelho (Não Perturbar) | "offline" → cinza (invisível)
def get_status_obj(status_type: str) -> disnake.Status:
    status_map = {
        "online":  disnake.Status.online,
        "idle":    disnake.Status.idle,
        "dnd":     disnake.Status.dnd,
        "offline": disnake.Status.offline,   # invisível
    }
    return status_map.get(status_type, disnake.Status.online)

# ── Tipos de atividade (texto exibido abaixo do nome) ─────────────────────────
# "custom"    → mensagem livre (sem prefixo)
# "playing"   → "Jogando <nome>"
# "listening" → "Ouvindo <nome>"
# "watching"  → "Assistindo <nome>"
# "streaming" → "Transmitindo <nome>"  (exige URL Twitch/YouTube)
# "competing" → "Competindo em <nome>"
def get_activity_obj(activity_type: str, name: str, stream_url: str = "") -> disnake.BaseActivity:
    url = stream_url.strip() if stream_url else "https://twitch.tv/discord"
    activity_map = {
        "playing":   lambda: disnake.Game(name=name),
        "listening": lambda: disnake.Activity(type=disnake.ActivityType.listening,  name=name),
        "watching":  lambda: disnake.Activity(type=disnake.ActivityType.watching,   name=name),
        "streaming": lambda: disnake.Streaming(name=name, url=url),
        "competing": lambda: disnake.Activity(type=disnake.ActivityType.competing,  name=name),
        "custom":    lambda: disnake.CustomActivity(name=name),
    }
    builder = activity_map.get(activity_type, activity_map["custom"])
    return builder()

@tasks.loop(seconds=5)
async def status_rotator_task(bot: disnake.Client):
    database = db.get_document("custom_status")

    tasks_list = database.get("tasks")
    if not tasks_list:
        old_type = database.get("type", "online")
        old_names = database.get("names", [])
        if not old_names and database.get("name"):
            old_names = [database.get("name")]
        if old_names:
            tasks_list = [{"type": old_type, "activity": "custom", "name": name} for name in old_names]
        else:
            tasks_list = []

    if not tasks_list:
        await bot.change_presence(status=disnake.Status.online, activity=None)
        return

    if not hasattr(bot, "_status_cycler") or getattr(bot, "_status_cache", []) != tasks_list:
        bot._status_cache = tasks_list
        bot._status_cycler = itertools.cycle(tasks_list)

    current_task = next(bot._status_cycler)
    status_obj    = get_status_obj(current_task.get("type", "online"))
    activity_type = current_task.get("activity", "custom")
    status_name   = current_task.get("name", "")
    stream_url    = current_task.get("stream_url", "")

    activity = get_activity_obj(activity_type, status_name, stream_url)
    await bot.change_presence(status=status_obj, activity=activity)
