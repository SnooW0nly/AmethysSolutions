import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, verificar_guild
from functions.emoji import emoji


class OnMemberJoin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: disnake.Member):
        if member.guild is None or not verificar_guild(member.guild.id):
            return

        canal_id = obter_canal_id("canal_de_logs_de_entradas")
        if not canal_id:
            return
        linhas = [
            f"{emoji.member} **Membro:** {member.mention} (`{member.id}`)",
            f"{emoji.calendar} **Conta criada:** <t:{int(member.created_at.timestamp())}:f> (<t:{int(member.created_at.timestamp())}:R>)",
            f"{emoji.members} **Total de membros:** {member.guild.member_count}",
        ]
        await enviar_log(member.guild, canal_id, "Logs de Entradas", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnMemberJoin(bot))