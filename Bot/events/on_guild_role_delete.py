import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji


class OnGuildRoleDelete(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_guild_role_delete")
    async def on_guild_role_delete(self, role: disnake.Role):
        if role.guild is None or not verificar_guild(role.guild.id):
            return
        canal_id = obter_canal_id("canal_de_logs_de_cargos_excluidos")
        if not canal_id:
            return
        executor = await buscar_executor_auditlog(
            role.guild,
            [disnake.AuditLogAction.role_delete],
            lambda e: getattr(e.target, "id", None) == role.id,
        )
        executor_str = executor.mention if executor and hasattr(executor, 'mention') else (str(executor) if executor else "Não identificado")

        linhas = [
            f"{emoji.role} **Cargo excluído:** **{role.name}** (`{role.id}`)",
            f"{emoji.wand} **Cor:** `{role.colour}`",
            f"{emoji.pin} **Menção:** `{role.mentionable}` | **Separado:** `{role.hoist}`",
            f"{emoji.member} **Executor:** {executor_str}{(f' (`{getattr(executor, 'id', None)}`)') if executor else ''}",
        ]
        await enviar_log(role.guild, canal_id, "Logs de Cargos - Excluídos", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnGuildRoleDelete(bot))


