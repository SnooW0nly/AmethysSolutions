"""
Sistema de hospedagem de transcripts — integrado à API Amethys
Usado ao fechar tickets (envia para o canal de logs com botão de link)
"""

import disnake
from disnake.ext import commands
import json
import os
from typing import Optional

from .donwload_transcript import upload_transcript_to_api, get_transcript_api_url


async def log_transcript(
    bot: commands.Bot,
    transcript_file: disnake.File,
    log_channel_id: int = None,
    message_to_reply: disnake.Message = None,
    guild_id: Optional[str] = None,
    guild_name: Optional[str] = None,
    ticket_id: Optional[str] = None,
    panel_id: Optional[str] = None,
    api_url: Optional[str] = None,
):
    """
    Faz upload do transcript para a API Amethys e envia o link no canal de logs.

    :param bot: Instância do bot
    :param transcript_file: Arquivo de transcript (disnake.File com HTML)
    :param log_channel_id: ID do canal de log (não usado, mantido por compatibilidade)
    :param message_to_reply: Mensagem de fechamento do ticket para responder
    :param guild_id: ID do servidor
    :param guild_name: Nome do servidor
    :param ticket_id: ID do ticket
    :param panel_id: ID do painel
    :param api_url: URL base da API (opcional, usa config_api.json)
    """
    if api_url is None:
        api_url = get_transcript_api_url()

    try:
        # Extrai nome do canal do filename
        channel_name = (
            transcript_file.filename.split('-', 1)[1].replace('.html', '')
            if '-' in transcript_file.filename
            else 'ticket'
        )

        # Lê o HTML
        transcript_file.fp.seek(0)
        transcript_html = transcript_file.fp.read().decode('utf-8')

        # Extrai channel_id do ticket_id se disponível
        channel_id = ticket_id

        # Faz upload
        transcript_url = await upload_transcript_to_api(
            transcript_html=transcript_html,
            channel_name=channel_name,
            channel_id=channel_id,
            guild_id=guild_id,
            guild_name=guild_name,
            ticket_id=ticket_id,
            panel_id=panel_id,
            ttl_days=3,
            api_url=api_url,
        )

        if transcript_url and message_to_reply:
            embed = disnake.Embed(
                title="📄 Transcript do Ticket",
                color=disnake.Color.from_rgb(138, 0, 196),
            )
            embed.add_field(
                name="Canal",
                value=f"`#{channel_name}`",
                inline=True,
            )
            embed.add_field(
                name="⏰ Expiração",
                value="Expira em **3 dias** automaticamente",
                inline=True,
            )
            embed.set_footer(text="Amethys Transcripts • Hospedado com segurança")

            try:
                await message_to_reply.reply(
                    embed=embed,
                    components=[
                        disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label="📋 Ver Transcript",
                                style=disnake.ButtonStyle.link,
                                url=transcript_url,
                            )
                        )
                    ],
                )
                print(f"[TRANSCRIPT] Log enviado com sucesso: {transcript_url}")
            except Exception as e:
                print(f"[TRANSCRIPT] Erro ao enviar embed no log: {e}")

        elif not transcript_url:
            print("[TRANSCRIPT] Falha ao fazer upload do transcript")
            if message_to_reply:
                try:
                    await message_to_reply.reply(
                        "⚠️ Não foi possível hospedar o transcript no momento."
                    )
                except Exception:
                    pass

    except Exception as e:
        print(f"[TRANSCRIPT] Erro geral em log_transcript: {e}")
        if message_to_reply:
            try:
                await message_to_reply.reply("⚠️ Erro ao processar o transcript.")
            except Exception:
                pass
