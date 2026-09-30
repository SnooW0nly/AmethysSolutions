import disnake
from disnake.ext import commands

from modules.tickets.transcripts import generate_transcript
from modules.tickets.transcripts.donwload_transcript import send_transcript_to_dm
from functions.emoji import emoji
from ..permissions import check_attendant_permissions


async def transcript(inter: disnake.MessageInteraction, bot: commands.Bot, limit: int = None):
    """
    Gera um transcript a partir de uma interação de botão e o envia para a DM do usuário.
    """
    await inter.response.defer(ephemeral=True)
    
    # Verificar permissões (atendentes ou dono do ticket podem gerar transcript)
    has_permission = await check_attendant_permissions(inter.author, inter.channel.id, check_bot_admin=True)
    if not has_permission:
        return await inter.followup.send(
            f"{emoji.wrong} Você não tem permissão para gerar transcript.",
            ephemeral=True
        )

    try:
        transcript_file = await generate_transcript(inter.channel, bot, limit=limit)

        if not transcript_file:
            await inter.followup.send(f"{emoji.wrong} Não foi possível gerar o transcript.", ephemeral=True)
            return

        await send_transcript_to_dm(inter, transcript_file)

    except Exception as e:
        print(f"Ocorreu um erro ao gerar o transcript via botão: {e}")
        await inter.followup.send(f"{emoji.wrong} Desculpe, ocorreu um erro inesperado.", ephemeral=True)
