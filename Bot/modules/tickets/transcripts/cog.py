import disnake
from disnake.ext import commands

from . import generate_transcript
from .donwload_transcript import send_transcript_to_dm
from functions.emoji import emoji


class TranscriptCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="transcript",
        description="Envia o transcript do canal para a sua DM."
    )
    async def transcript(self, interaction: disnake.ApplicationCommandInteraction, limit: int = None):
        """
        Gera um transcript e o envia para a DM do autor do comando.

        Parameters
        ----------
        limit: O número máximo de mensagens para incluir no transcript.
        """
        await interaction.response.defer(ephemeral=True)

        try:
            transcript_file = await generate_transcript(interaction.channel, self.bot, limit=limit)

            if not transcript_file:
                await interaction.followup.send(f"{emoji.wrong} Não foi possível gerar o transcript.", ephemeral=True)
                return

            await send_transcript_to_dm(interaction, transcript_file)

        except Exception as e:
            print(f"Ocorreu um erro ao gerar o transcript: {e}")
            await interaction.follow_up.send(f"{emoji.wrong} Desculpe, ocorreu um erro inesperado.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(TranscriptCog(bot))
