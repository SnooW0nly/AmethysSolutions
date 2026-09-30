import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji


class OnMemberUpdateTimeout(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_update")
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        if after.guild is None or not verificar_guild(after.guild.id):
            return
        canal_id = obter_canal_id("canal_de_logs_de_castigos")
        if not canal_id:
            return
        before_to = getattr(before, "timed_out_until", None)
        after_to = getattr(after, "timed_out_until", None)
        if before_to == after_to:
            return

        if after_to and (not before_to or after_to != before_to):
            executor = await buscar_executor_auditlog(
                after.guild,
                [disnake.AuditLogAction.member_update, disnake.AuditLogAction.member_disconnect],
                lambda e: getattr(e.target, "id", None) == after.id,
            )
            executor_str = executor.mention if executor and hasattr(executor, 'mention') else (str(executor) if executor else "Não identificado")

            linhas = [
                f"{emoji.member} **Membro:** {after.mention} (`{after.id}`)",
                f"{emoji.clock} **Castigo aplicado até:** <t:{int(after_to.timestamp())}:f> (<t:{int(after_to.timestamp())}:R>)",
                f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
            ]
            await enviar_log(after.guild, canal_id, "Logs de Castigos - Aplicados", linhas)
            
        elif before_to and not after_to:
            executor = await buscar_executor_auditlog(
                after.guild,
                [disnake.AuditLogAction.member_update],
                lambda e: getattr(e.target, "id", None) == after.id,
            )
            executor_str = executor.mention if executor and hasattr(executor, 'mention') else (str(executor) if executor else "Não identificado")

            linhas = [
                f"{emoji.member} **Membro:** {after.mention} (`{after.id}`)",
                f"{emoji.unlock} **Castigo removido**",
                f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
            ]
            await enviar_log(after.guild, canal_id, "Logs de Castigos - Removidos", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnMemberUpdateTimeout(bot))
