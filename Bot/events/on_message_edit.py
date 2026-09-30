import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, verificar_guild
from functions.emoji import emoji


class OnMessageEdit(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message_edit")
    async def on_message_edit(self, before: disnake.Message, after: disnake.Message):
        if after.guild is None or after.author.bot or not verificar_guild(after.guild.id):
            return

        if before.content == after.content:
            return

        canal_id = obter_canal_id("canal_de_logs_de_mensagens")
        if not canal_id:
            return
        executor = after.author
        linhas = [
            f"{emoji.message} **Mensagem editada em:** {after.channel.mention} (`{after.channel.id}`)",
            f"{emoji.member} **Executor:** {executor.mention if hasattr(executor, 'mention') else executor} (`{getattr(executor, 'id', 'desconhecido')}`)\n",
            f"{emoji.minus} **Antes:**\n```\n{(before.content or '(vazio)')[:900]}\n```",
            f"{emoji.plus} **Depois:**\n```\n{(after.content or '(vazio)')[:900]}\n```",
        ]
        botao = disnake.ui.Button(label="Ir para a mensagem", url=after.jump_url, style=disnake.ButtonStyle.link)
        row = disnake.ui.ActionRow(botao)
        await enviar_log(after.guild, canal_id, "Logs de Mensagens - Editadas", linhas, extra_components=[row])


def setup(bot: commands.Bot):
    bot.add_cog(OnMessageEdit(bot))