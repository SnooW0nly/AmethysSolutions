import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji


class OnMemberUpdatePermissions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_update")
    async def on_member_update(self, before: disnake.Member, after: disnake.Member):
        if after.guild is None or not verificar_guild(after.guild.id):
            return
        canal_add = obter_canal_id("canal_de_logs_de_permissoes_adicionadas")
        canal_rem = obter_canal_id("canal_de_logs_de_permissoes_removidas")
        if not canal_add and not canal_rem:
            return

        try:
            perms_before = dict(before.guild_permissions)
            perms_after = dict(after.guild_permissions)
        except Exception:
            return

        adicionadas = [name for name in perms_after.keys() if perms_before.get(name) is not True and perms_after.get(name) is True]
        removidas = [name for name in perms_before.keys() if perms_before.get(name) is True and perms_after.get(name) is not True]
        if not adicionadas and not removidas:
            return

        executor = await buscar_executor_auditlog(
            after.guild,
            [disnake.AuditLogAction.member_role_update, disnake.AuditLogAction.member_update],
            lambda e: getattr(e.target, "id", None) == after.id,
        )
        executor_str = executor.mention if executor and hasattr(executor, 'mention') else (str(executor) if executor else "Não identificado")

        if adicionadas and canal_add:
            linhas = [
                f"{emoji.member} **Alvo:** {after.mention} (`{after.id}`)",
                f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
            ]
            for nome in sorted(adicionadas)[:25]:
                linhas.append(f"{emoji.plus} **Adicionada:** `{nome}`")
            await enviar_log(after.guild, canal_add, "Logs de Permissões - Adicionadas (por cargos)", linhas)

        if removidas and canal_rem:
            linhas = [
                f"{emoji.member} **Alvo:** {after.mention} (`{after.id}`)",
                f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
            ]
            for nome in sorted(removidas)[:25]:
                linhas.append(f"{emoji.minus} **Removida:** `{nome}`")
            await enviar_log(after.guild, canal_rem, "Logs de Permissões - Removidas (por cargos)", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnMemberUpdatePermissions(bot))


