"""
Sistema de download/envio de transcripts para DM
Usa a API interna do backend Amethys para hospedar os transcripts
"""

import disnake
from functions.emoji import emoji
from functions.database import database as db
import json
import os
import aiohttp
from typing import Optional


def get_transcript_api_url() -> str:
    """
    Retorna a URL base da API de transcripts.
    Lê do config_api.json ou da variável de ambiente TRANSCRIPT_API_URL.
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__), '../../../configs/config_api.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        api_host = config.get('transcripts', 'localhost:8080')

        if not api_host.startswith('http'):
            api_host = f'http://{api_host}'

        return api_host.rstrip('/')
    except Exception as e:
        print(f"[TRANSCRIPT] Erro ao carregar config_api.json: {e}")
        return os.getenv("TRANSCRIPT_API_URL", "http://localhost:8080")


def get_api_key() -> Optional[str]:
    """Retorna a chave da API de transcript."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '../../../configs/config_api.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('transcript_api_key') or os.getenv("TRANSCRIPT_API_KEY") or os.getenv("CYM_API_KEY")
    except Exception:
        return os.getenv("TRANSCRIPT_API_KEY") or os.getenv("CYM_API_KEY")


async def upload_transcript_to_api(
    transcript_html: str,
    channel_name: str,
    channel_id: Optional[str] = None,
    guild_id: Optional[str] = None,
    guild_name: Optional[str] = None,
    ticket_id: Optional[str] = None,
    panel_id: Optional[str] = None,
    generated_by_id: Optional[str] = None,
    generated_by_username: Optional[str] = None,
    ttl_days: int = 3,
    api_url: Optional[str] = None,
) -> Optional[str]:
    """
    Faz upload do transcript para a API Amethys.

    :return: URL completa do transcript ou None se falhar
    """
    if api_url is None:
        api_url = get_transcript_api_url()

    api_key = get_api_key()

    try:
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()

            # Arquivo HTML
            data.add_field(
                'file',
                transcript_html.encode('utf-8'),
                filename=f'transcript-{channel_name}.html',
                content_type='text/html',
            )

            # Campos extras
            data.add_field('filename', f'transcript-{channel_name}.html')
            data.add_field('channel_name', channel_name)
            data.add_field('ttl_days', str(ttl_days))

            if channel_id:
                data.add_field('channel_id', str(channel_id))
            if guild_id:
                data.add_field('guild_id', str(guild_id))
            if guild_name:
                data.add_field('guild_name', guild_name)
            if ticket_id:
                data.add_field('ticket_id', str(ticket_id))
            if panel_id:
                data.add_field('panel_id', str(panel_id))
            if generated_by_id:
                data.add_field('generated_by_id', str(generated_by_id))
            if generated_by_username:
                data.add_field('generated_by_username', generated_by_username)

            headers = {}
            if api_key:
                headers['X-API-Key'] = api_key

            async with session.post(
                f"{api_url}/api/v1/transcript/upload",
                data=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success"):
                        full_url = result.get('fullUrl') or result.get('url')
                        if full_url and not full_url.startswith('http'):
                            full_url = f"{api_url}{full_url}"
                        print(f"[TRANSCRIPT] Upload bem-sucedido: {full_url}")
                        return full_url
                    else:
                        print(f"[TRANSCRIPT] API retornou erro: {result}")
                elif resp.status == 401:
                    print("[TRANSCRIPT] Erro de autenticação — verifique TRANSCRIPT_API_KEY")
                else:
                    err_text = await resp.text()
                    print(f"[TRANSCRIPT] Erro ao fazer upload: Status {resp.status} — {err_text[:200]}")

    except aiohttp.ClientConnectorError:
        print(f"[TRANSCRIPT] Não foi possível conectar à API em {api_url}")
    except Exception as e:
        print(f"[TRANSCRIPT] Erro ao fazer upload: {e}")

    return None


async def send_transcript_to_dm(
    interaction: disnake.ApplicationCommandInteraction,
    transcript_file: disnake.File,
):
    """
    Envia o transcript gerado para a DM do usuário via link da API.

    :param interaction: A interação do comando.
    :param transcript_file: O arquivo de transcript gerado.
    """
    config = db.get_document("tickets_config") or {}
    tickets_data = db.get_document("tickets_data") or {}

    # Tenta identificar o painel do ticket
    panel_id = None
    ticket_id = None
    if isinstance(interaction.channel, (disnake.TextChannel, disnake.Thread)):
        for pid, users in tickets_data.get("panels", {}).items():
            for user_id, tickets in users.items():
                for ticket in tickets:
                    if ticket.get("ticket_id") == interaction.channel.id:
                        panel_id = pid
                        ticket_id = str(interaction.channel.id)
                        break
                if panel_id:
                    break
            if panel_id:
                break

    panel_data = config.get("panels", {}).get(panel_id, {}) if panel_id else {}
    messages = panel_data.get("messages", {})

    message_template = messages.get(
        "transcript_dm_message",
        "Aqui está o transcript que você solicitou para o ticket `{channel_name}`:",
    )
    message_content = message_template.format(
        channel_name=interaction.channel.name,
        guild_name=interaction.guild.name,
        user_mention=interaction.author.mention,
        user_name=interaction.author.name,
    )

    try:
        # Lê o HTML do arquivo
        transcript_file.fp.seek(0)
        transcript_html = transcript_file.fp.read().decode('utf-8')

        transcript_url = await upload_transcript_to_api(
            transcript_html=transcript_html,
            channel_name=interaction.channel.name,
            channel_id=str(interaction.channel.id),
            guild_id=str(interaction.guild.id),
            guild_name=interaction.guild.name,
            ticket_id=ticket_id,
            panel_id=panel_id,
            generated_by_id=str(interaction.author.id),
            generated_by_username=str(interaction.author.name),
            ttl_days=3,
        )

        if transcript_url:
            await interaction.author.send(
                content=message_content,
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
            await interaction.followup.send(
                f"{emoji.double_check} Transcript enviado para sua DM!",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"{emoji.wrong} Não foi possível hospedar o transcript. Tente novamente mais tarde.",
                ephemeral=True,
            )

    except disnake.Forbidden:
        await interaction.followup.send(
            f"{emoji.wrong} Não consegui enviar o transcript para sua DM. Verifique se suas DMs estão abertas.",
            ephemeral=True,
        )
    except Exception as e:
        print(f"[TRANSCRIPT] Erro ao enviar para DM: {e}")
        await interaction.followup.send(
            f"{emoji.wrong} Ocorreu um erro ao processar o transcript.",
            ephemeral=True,
        )
