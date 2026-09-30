import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji


class OnMemberUpdateRoles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_update")
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        if after.guild is None or not verificar_guild(after.guild.id):
            return

        canal_add = obter_canal_id("canal_de_logs_de_cargos_adicionados")
        canal_rem = obter_canal_id("canal_de_logs_de_cargos_removidos")
        if not canal_add and not canal_rem:
            return

        adicionados = [r for r in after.roles if r not in before.roles]
        removidos = [r for r in before.roles if r not in after.roles]
        if not adicionados and not removidos:
            return

        executor = await buscar_executor_auditlog(
            after.guild,
            [disnake.AuditLogAction.member_role_update, disnake.AuditLogAction.member_update],
            lambda e: getattr(e.target, "id", None) == after.id,
        )
        executor_str = executor.mention if executor and hasattr(executor, "mention") else (str(executor) if executor else "Não identificado")

        if adicionados and canal_add:
            linhas = [
                f"{emoji.member} **Membro:** {after.mention} (`{after.id}`)",
                f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
            ]
            for r in adicionados:
                linhas.append(f"{emoji.plus} **Cargo adicionado:** {r.mention} (`{r.id}`)")
            await enviar_log(after.guild, canal_add, "Logs de Cargos - Adicionados", linhas)

        if removidos and canal_rem:
            linhas = [
                f"{emoji.member} **Membro:** {after.mention} (`{after.id}`)",
                f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
            ]
            for r in removidos:
                linhas.append(f"{emoji.minus} **Cargo removido:** {r.mention} (`{r.id}`)")
            await enviar_log(after.guild, canal_rem, "Logs de Cargos - Removidos", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnMemberUpdateRoles(bot))