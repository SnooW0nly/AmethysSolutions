import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji


class OnGuildChannelUpdate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_guild_channel_update")
    async def on_guild_channel_update(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        if after.guild is None or not verificar_guild(after.guild.id):
            return
        
        canal_id = obter_canal_id("canal_de_logs_de_canais_editados")
        if not canal_id:
            return

        # Detect changes
        changes = []
        
        if before.name != after.name:
            changes.append(f"{emoji.edit} **Nome:** `{before.name}` → `{after.name}`")
        
        if hasattr(before, 'topic') and hasattr(after, 'topic') and before.topic != after.topic:
            before_topic = before.topic or "Nenhum"
            after_topic = after.topic or "Nenhum"
            changes.append(f"{emoji.edit} **Tópico:** `{before_topic}` → `{after_topic}`")
        
        if hasattr(before, 'slowmode_delay') and hasattr(after, 'slowmode_delay') and before.slowmode_delay != after.slowmode_delay:
            changes.append(f"{emoji.clock} **Modo lento:** `{before.slowmode_delay}s` → `{after.slowmode_delay}s`")
        
        if hasattr(before, 'nsfw') and hasattr(after, 'nsfw') and before.nsfw != after.nsfw:
            changes.append(f"{emoji.warn} **NSFW:** `{before.nsfw}` → `{after.nsfw}`")
        
        if before.category != after.category:
            before_cat = before.category.name if before.category else "Nenhuma"
            after_cat = after.category.name if after.category else "Nenhuma"
            changes.append(f"{emoji.folder} **Categoria:** `{before_cat}` → `{after_cat}`")
        
        if before.position != after.position:
            changes.append(f"{emoji.arrow} **Posição:** `{before.position}` → `{after.position}`")

        # Only log if there are meaningful changes
        if not changes:
            return

        executor = await buscar_executor_auditlog(
            after.guild,
            [disnake.AuditLogAction.channel_update],
            lambda e: getattr(e.target, "id", None) == after.id,
        )
        executor_str = executor.mention if executor and hasattr(executor, 'mention') else (str(executor) if executor else "Não identificado")

        linhas = [
            f"{emoji.textc} **Canal:** {after.mention} (`{after.id}`)",
            f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
            "",
            "**Alterações:**"
        ]
        linhas.extend(changes)

        await enviar_log(after.guild, canal_id, "Logs de Canais - Editados", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnGuildChannelUpdate(bot))
