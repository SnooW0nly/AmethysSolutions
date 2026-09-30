import disnake
from disnake.ext import commands
import traceback

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji
from functions.database import database as db
from modules.tickets.functions.setup_functions.close_ticket import close_ticket


class OnMemberRemove(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def auto_close_tickets(self, member: disnake.Member):
        tickets_data = db.obter("database/tickets/tickets_data.json")
        config = db.obter("database/tickets/tickets_config.json")
        
        if not tickets_data or not config:
            return

        user_id_str = str(member.id)
        
        for panel_id, users in tickets_data.get("panels", {}).items():
            if user_id_str in users:
                panel_data = config.get("panels", {}).get(panel_id, {})
                auto_close_pref = panel_data.get("preferences", {}).get("auto_close", {})
                user_left_pref = auto_close_pref.get("user_left", {})
                
                if not user_left_pref.get("enabled", False):
                    continue

                open_tickets = [t for t in users[user_id_str] if t.get("status") == "open"]

                for ticket in open_tickets:
                    channel = self.bot.get_channel(ticket.get("ticket_id"))
                    if channel:
                        try:
                            reason = "O usuário saiu do servidor."
                            await close_ticket(
                                bot=self.bot,
                                channel=channel,
                                closed_by=member.guild.me,
                                reason=reason,
                                inter=None
                            )
                        except Exception:
                            traceback.print_exc()

    @commands.Cog.listener("on_member_remove")
    async def on_member_remove(self, member: disnake.Member):
        if member.guild is None or not verificar_guild(member.guild.id):
            return

        await self.auto_close_tickets(member)

        canal_expulsoes = obter_canal_id("canal_de_logs_de_expusoes")
        canal_saidas = obter_canal_id("canal_de_logs_de_saidas")
        if not canal_expulsoes and not canal_saidas:
            return

        executor = None
        try:
            executor = await buscar_executor_auditlog(
                member.guild,
                [disnake.AuditLogAction.kick],
                lambda e: getattr(e.target, "id", None) == member.id,
            )
        except Exception:
            executor = None

        if executor and canal_expulsoes:
            executor_str = (
                (executor.mention if hasattr(executor, "mention") else str(executor))
                + (f" (`{getattr(executor, 'id', None)}`)" if getattr(executor, "id", None) else "")
            )
            linhas = [
                f"{emoji.member} **Alvo:** {member.mention if hasattr(member, 'mention') else str(member)} (`{getattr(member, 'id', 'desconhecido')}`)",
                f"{emoji.member} **Executor:** {executor_str}",
            ]
            await enviar_log(member.guild, canal_expulsoes, "Logs de Expulsões", linhas)
            return

        if canal_saidas:
            linhas = [
                f"{emoji.member} **Membro:** {member.name} (`{member.id}`)",
                f"{emoji.calendar} **Conta criada:** <t:{int(member.created_at.timestamp())}:f> (<t:{int(member.created_at.timestamp())}:R>)",
                f"{emoji.members} **Total de membros:** {member.guild.member_count}",
            ]
            await enviar_log(member.guild, canal_saidas, "Logs de Saídas", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnMemberRemove(bot))