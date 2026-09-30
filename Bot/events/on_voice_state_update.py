import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji


class OnVoiceStateUpdate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if member.guild is None or not verificar_guild(member.guild.id):
            return

        canal_id = obter_canal_id("canal_de_logs_de_trafego_em_call")
        if not canal_id:
            return

        is_move = bool(before.channel and after.channel and before.channel != after.channel)
        eventos = []
        if before.channel != after.channel:
            if before.channel is None and after.channel is not None:
                eventos.append(f"Entrou em call: {after.channel.mention}")
            elif before.channel is not None and after.channel is None:
                eventos.append(f"Saiu da call: {before.channel.mention}")

        if before.self_stream != after.self_stream:
            eventos.append("Iniciou streaming" if after.self_stream else "Parou streaming")
        if before.self_mute != after.self_mute:
            eventos.append("Mutou o microfone" if after.self_mute else "Desmutou o microfone")
        if before.self_deaf != after.self_deaf:
            eventos.append("Mutou o áudio" if after.self_deaf else "Desmutou o áudio")
        if before.mute != after.mute:
            eventos.append("Foi mutado pelo servidor" if after.mute else "Foi desmutado pelo servidor")
        if before.deaf != after.deaf:
            eventos.append("Foi ensurdecido pelo servidor" if after.deaf else "Deixou de ser ensurdecido")

        if not eventos and not is_move:
            return

        executor = None
        if is_move:
            try:
                executor = await buscar_executor_auditlog(
                    member.guild,
                    [disnake.AuditLogAction.member_move],
                    lambda e: getattr(e.target, "id", None) == member.id,
                )
            except Exception:
                executor = None

        linhas = []
        if is_move:
            if executor:
                linhas.append(f"{emoji.member} {executor.mention} (`{getattr(executor, 'id', 'desconhecido')}`) moveu {member.mention} (`{member.id}`)")
            else:
                linhas.append(f"{emoji.member} {member.mention} (`{member.id}`) moveu-se")
            if before.channel and after.channel:
                linhas.append(f"{emoji.route} {before.channel.mention} ➜ {after.channel.mention}")
        else:
            linhas.append(f"{emoji.member} **Membro:** {member.mention} (`{member.id}`)")
            linhas.extend([f"{emoji.route} {e}" for e in eventos])
        await enviar_log(member.guild, canal_id, "Logs de Tráfego em Call", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnVoiceStateUpdate(bot))