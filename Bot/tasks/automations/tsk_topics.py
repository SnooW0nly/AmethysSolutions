import disnake
from disnake.ext import commands
from functions.database import database as db
from modules.automations.topics.helpers import TopicsDB

class TopicsTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message_create_thread(self, message: disnake.Message):
        try:
            if message.author.bot or not isinstance(message.author, disnake.Member):
                return

            config = TopicsDB.carregar_config()
            if not config.get("ativado", False):
                return

            immune_role_id = config.get("immune_role_id")
            if immune_role_id:
                if any(role.id == immune_role_id for role in message.author.roles):
                    return

            topicos = config.get("topicos", [])
            if not topicos:
                return
            for entry in topicos:
                try:
                    if int(entry.get("channel_id")) != message.channel.id:
                        continue
                except Exception:
                    continue
                try:
                    thread = await message.create_thread(name=entry.get("name") or "Tópico")
                except Exception:
                    continue
                content_template = entry.get("content") or ""
                content = content_template.replace("{user}", message.author.mention)
                try:
                    await thread.send(content)
                except Exception:
                    pass
                if bool(entry.get("locked", False)):
                    try:
                        await thread.edit(locked=True)
                    except Exception:
                        pass
        except Exception:
            return

def setup(bot: commands.Bot):
    bot.add_cog(TopicsTasks(bot))
