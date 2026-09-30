import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji


class OnMemberBan(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_ban")
    async def on_member_ban(self, guild: disnake.Guild, user: disnake.abc.User):
        if guild is None or not verificar_guild(guild.id):
            return
        canal_id = obter_canal_id("canal_de_logs_de_banimentos")
        if not canal_id:
            return
        try:
            executor = await buscar_executor_auditlog(
                guild,
                [disnake.AuditLogAction.ban],
                lambda e: getattr(getattr(e, "target", None), "id", None) == getattr(user, "id", None),
            )
            executor_str = (
                (executor.mention if hasattr(executor, "mention") else str(executor))
                + (f" (`{getattr(executor, 'id', None)}`)" if getattr(executor, "id", None) else "")
            ) if executor else "Não identificado"

            linhas = [
                f"{emoji.member} **Alvo:** {user.mention if hasattr(user, 'mention') else str(user)} (`{getattr(user, 'id', 'desconhecido')}`)",
                f"{emoji.member} **Executor:** {executor_str}",
            ]
            await enviar_log(guild, canal_id, "Logs de Banimentos", linhas)
        except Exception:
            return


def setup(bot: commands.Bot):
    bot.add_cog(OnMemberBan(bot))


