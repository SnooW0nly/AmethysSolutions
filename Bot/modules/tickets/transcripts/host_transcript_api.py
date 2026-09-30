"""
Sistema de hospedagem de transcripts usando a API Vision
Versão alternativa - Lê a URL da API do config_api.json
"""

import disnake
from disnake.ext import commands
import aiohttp
import json
import os
from typing import Optional


def get_transcript_api_url() -> str:
    """Carrega a URL da API de transcripts do config_api.json"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), '../../../configs/config_api.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        api_host = config.get('transcripts', 'localhost:22222')
        
        # Garantir que tenha protocolo
        if not api_host.startswith('http'):
            api_host = f'http://{api_host}'
        
        return api_host
    except Exception as e:
        print(f"[TRANSCRIPT] Erro ao carregar config_api.json: {e}")
        return os.getenv("TRANSCRIPT_API_URL", "http://localhost:22222")


async def upload_transcript_to_api(
    transcript_html: str,
    channel_name: str,
    api_url: str = None
) -> Optional[str]:
    """
    Faz upload do transcript para a API e retorna a URL.
    
    :param transcript_html: Conteúdo HTML do transcript
    :param channel_name: Nome do canal (para o nome do arquivo)
    :param api_url: URL base da API (usa config_api.json se não fornecida)
    :return: URL do transcript ou None se falhar
    """
    if api_url is None:
        api_url = get_transcript_api_url()
    
    try:
        async with aiohttp.ClientSession() as session:
            # Preparar o arquivo
            data = aiohttp.FormData()
            data.add_field(
                'file',
                transcript_html.encode('utf-8'),
                filename=f'transcript-{channel_name}.html',
                content_type='text/html'
            )
            data.add_field('filename', f'transcript-{channel_name}.html')
            data.add_field('channel_name', channel_name)
            
            # Fazer upload - nova rota /api/v1/transcript/upload
            async with session.post(
                f"{api_url}/api/v1/transcript/upload",
                data=data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("success"):
                        # Usar fullUrl se disponível
                        if result.get('fullUrl'):
                            full_url = result['fullUrl']
                        else:
                            url_path = result['url']
                            if url_path.startswith('/'):
                                full_url = f"{api_url}{url_path}"
                            else:
                                full_url = url_path
                        
                        print(f"[TRANSCRIPT] Upload bem-sucedido: {full_url}")
                        return full_url
                else:
                    print(f"[TRANSCRIPT] Erro ao fazer upload: Status {resp.status}")
                    return None
    except Exception as e:
        print(f"[TRANSCRIPT] Erro ao fazer upload: {e}")
        return None


async def log_transcript(
    bot: commands.Bot,
    transcript_file: disnake.File,
    log_channel_id: int = None,
    message_to_reply: disnake.Message = None,
    api_url: str = None
):
    """
    Faz upload do transcript para a API e envia a URL no Discord.
    
    :param bot: Instância do bot
    :param transcript_file: Arquivo de transcript (contém o HTML)
    :param log_channel_id: ID do canal de log (não usado nesta versão)
    :param message_to_reply: Mensagem para responder
    :param api_url: URL base da API
    """
    if api_url is None:
        api_url = get_transcript_api_url()
    
    try:
        # Extrair o nome do canal do nome do arquivo
        channel_name = transcript_file.filename.split('-', 1)[1].replace('.html', '') if '-' in transcript_file.filename else 'ticket'
        
        # Ler o conteúdo do arquivo
        transcript_file.fp.seek(0)
        transcript_html = transcript_file.fp.read().decode('utf-8')
        
        # Fazer upload para a API
        transcript_url = await upload_transcript_to_api(
            transcript_html,
            channel_name,
            api_url
        )
        
        if transcript_url and message_to_reply:
            # Criar embed com a URL
            embed = disnake.Embed(
                title="📄 Transcript do Ticket",
                description=f"[Clique aqui para visualizar o transcript]({transcript_url})",
                color=disnake.Color.green()
            )
            embed.add_field(
                name="⏰ Expiração",
                value="Este transcript expirará automaticamente em **3 dias**",
                inline=False
            )
            embed.set_footer(text="Transcript hospedado com segurança")
            
            try:
                await message_to_reply.reply(embed=embed)
                print(f"[TRANSCRIPT] Embed enviado com sucesso")
            except Exception as e:
                print(f"[TRANSCRIPT] Erro ao enviar embed: {e}")
        elif not transcript_url:
            print(f"[TRANSCRIPT] Falha ao fazer upload do transcript")
            if message_to_reply:
                try:
                    await message_to_reply.reply(
                        "⚠️ Não foi possível hospedar o transcript. Tente novamente mais tarde."
                    )
                except Exception:
                    pass
                    
    except Exception as e:
        print(f"[TRANSCRIPT] Erro geral: {e}")
        if message_to_reply:
            try:
                await message_to_reply.reply(
                    "⚠️ Erro ao processar o transcript."
                )
            except Exception:
                pass
