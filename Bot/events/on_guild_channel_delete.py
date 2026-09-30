import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji

class OnGuildChannelDelete(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel: disnake.abc.GuildChannel):
        if channel.guild is None or not verificar_guild(channel.guild.id):
            return
        canal_id = obter_canal_id("canal_de_logs_de_canais_excluidos")
        if not canal_id:
            return
        tipo = getattr(channel.type, "name", str(channel.type)).capitalize()
        executor = await buscar_executor_auditlog(
            channel.guild,
            [disnake.AuditLogAction.channel_delete],
            lambda e: getattr(e.target, "id", None) == channel.id,
        )
        executor_str = executor.mention if executor and hasattr(executor, "mention") else (str(executor) if executor else "Não identificado")

        linhas = [
            f"{emoji.textc} **Canal excluído:** **{channel.name}**",
            f"{emoji.textc} **Tipo:** {tipo}",
            f"{emoji.textc} **ID:** `{channel.id}`",
            f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
        ]
        await enviar_log(channel.guild, canal_id, "Logs de Canais - Excluídos", linhas)

def setup(bot: commands.Bot):
    bot.add_cog(OnGuildChannelDelete(bot))


