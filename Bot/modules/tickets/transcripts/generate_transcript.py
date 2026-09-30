import disnake
import chat_exporter as dht
import io
import re
from disnake.ext import commands


def translate_to_pt_br(html_content: str) -> str:
    """
    Traduz os textos em inglês do transcript para português brasileiro.
    Usa substituições específicas para não quebrar URLs e atributos HTML.
    """
    result = html_content
    
    # === HTML lang ===
    result = result.replace('lang="en"', 'lang="pt-BR"')
    
    # === Cabeçalhos e Introdução (textos específicos) ===
    result = result.replace('>Welcome to #', '>Bem-vindo ao #')
    result = result.replace('This is the start of the #', 'Este é o início do canal #')
    result = result.replace(' channel.</span>', '.</span>')
    result = result.replace(' channel.<', '.<')
    
    # === Footer (texto específico) ===
    result = result.replace('>This transcript was generated on ', '>Este transcript foi gerado em ')
    result = result.replace('class="footer__text">This transcript was generated on ', 
                           'class="footer__text">Este transcript foi gerado em ')
    
    # === Meta description (texto específico) ===
    result = re.sub(
        r'Transcript of channel ([^"]+) from ([^"]+) with (\d+) messages',
        r'Transcript do canal \1 de \2 com \3 mensagens',
        result
    )
    
    # === Meses (apenas em contextos de texto, não URLs) ===
    months_en = ['January', 'February', 'March', 'April', 'May', 'June', 
                 'July', 'August', 'September', 'October', 'November', 'December']
    months_pt = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    for en, pt in zip(months_en, months_pt):
        # Substituir em contextos de texto (após números ou espaços)
        result = re.sub(rf'(\d{{1,2}}) {en}', rf'\1 {pt}', result)
        result = re.sub(rf'{en} (\d{{1,2}})', rf'{pt} \1', result)
    
    # === Dias da semana (apenas em data-timestamp) ===
    days_en = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    days_pt = ['Domingo', 'Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado']
    
    for en, pt in zip(days_en, days_pt):
        result = result.replace(f'data-timestamp="{en}', f'data-timestamp="{pt}')
    
    # === Timestamps relativos (textos específicos) ===
    result = result.replace('>Today at ', '>Hoje às ')
    result = result.replace('>Yesterday at ', '>Ontem às ')
    result = result.replace('>Tomorrow at ', '>Amanhã às ')
    
    # === Summary/Resumo (textos dentro de tags específicas) ===
    result = result.replace('>Summary<', '>Resumo<')
    result = result.replace('>Guild ID<', '>ID do Servidor<')
    result = result.replace('>Channel ID<', '>ID do Canal<')
    result = result.replace('>Channel Creation Date<', '>Data de Criação do Canal<')
    result = result.replace('>Total Message Count<', '>Total de Mensagens<')
    result = result.replace('>Total Message Participants<', '>Total de Participantes<')
    
    # === Informações do Membro ===
    result = result.replace('>Member Since<', '>Membro desde<')
    result = result.replace('>Member ID<', '>ID do Membro<')
    result = result.replace('>Message Count<', '>Mensagens Enviadas<')
    
    # === Menu de Contexto ===
    result = result.replace('>Copy Message ID<', '>Copiar ID da Mensagem<')
    
    # === Corrigir "at HH:MM" para "às HH:MM" em contextos de texto ===
    result = re.sub(r'>(\d{1,2} de \w+ de \d{4}) at (\d{1,2}:\d{2})', r'>\1 às \2', result)
    result = re.sub(r'"(\d{1,2} de \w+ de \d{4}) at (\d{1,2}:\d{2})', r'"\1 às \2', result)
    
    # === Formato de data brasileiro ===
    result = re.sub(
        r'(\d{1,2}) (Janeiro|Fevereiro|Março|Abril|Maio|Junho|Julho|Agosto|Setembro|Outubro|Novembro|Dezembro) (\d{4})',
        r'\1 de \2 de \3',
        result
    )
    
    return result


async def generate_transcript(channel: disnake.TextChannel, bot: commands.Bot, limit: int = None) -> disnake.File | None:
    """
    Gera um arquivo de transcript em HTML para um canal específico.
    O transcript é automaticamente traduzido para português brasileiro.

    :param channel: O canal do qual gerar o transcript.
    :param bot: A instância do bot para buscar membros fora da guilda.
    :param limit: O número máximo de mensagens a serem incluídas.
    :return: Um objeto disnake.File contendo o transcript, ou None se falhar.
    """
    try:
        transcript_html = await dht.export(
            channel,
            limit=limit,
            bot=bot,
        )

        if not transcript_html:
            return None

        # Traduzir para português brasileiro
        transcript_html = translate_to_pt_br(transcript_html)

        return disnake.File(
            io.BytesIO(transcript_html.encode()),
            filename=f"transcript-{channel.name}.html",
        )
    except Exception as e:
        print(f"Falha ao gerar transcript: {e}")
        return None
