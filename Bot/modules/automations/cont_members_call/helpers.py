import base64
from functions.database import database as db

def carregar_config() -> dict:
    """Carrega a configuração do MongoDB."""
    return db.get_document("automations_cont_members_call")

def salvar_config(data: dict) -> None:
    """Salva a configuração no MongoDB."""
    db.save_document("automations_cont_members_call", {}, data)

def sanitizar_prefixo(prefixo: str) -> str:
    """Remove caracteres inválidos do prefixo que não podem estar em nomes de canais/categorias."""
    # Caracteres inválidos em nomes de canais Discord: / \ < > : * ? " |
    caracteres_invalidos = ['/', '\\', '<', '>', ':', '*', '?', '"', '|']
    prefixo_sanitizado = prefixo
    for char in caracteres_invalidos:
        prefixo_sanitizado = prefixo_sanitizado.replace(char, '')
    # Remove espaços extras e limita o tamanho
    prefixo_sanitizado = ' '.join(prefixo_sanitizado.split())
    return prefixo_sanitizado[:50]  # Limita a 50 caracteres

def codificar_prefixo(prefixo: str) -> str:
    """Codifica o prefixo em base64 para uso seguro em custom_id."""
    return base64.urlsafe_b64encode(prefixo.encode('utf-8')).decode('utf-8')

def decodificar_prefixo(prefixo_codificado: str) -> str:
    """Decodifica o prefixo de base64."""
    try:
        return base64.urlsafe_b64decode(prefixo_codificado.encode('utf-8')).decode('utf-8')
    except Exception:
        return prefixo_codificado  # Retorna o original se falhar

def formatar_nome_contador(prefixo: str, contagem: int, estilo: int) -> str:
    """Formata o nome do contador com base no estilo."""
    estilos = {
        0: f"{prefixo}: {contagem}",
        1: f"{prefixo} {contagem}",
        2: f"{contagem} {prefixo}",
        3: f"{contagem}: {prefixo}",
    }
    return estilos.get(estilo, estilos[0])

def estilo_legenda(estilo: int) -> str:
    """Retorna a legenda descritiva para um estilo."""
    legendas = {
        0: "Prefixo: Contagem",
        1: "Prefixo Contagem",
        2: "Contagem Prefixo",
        3: "Contagem: Prefixo",
    }
    return legendas.get(estilo, legendas[0])

def contar_membros_em_call(guild) -> int:
    """Conta quantos membros estão em canais de voz no servidor."""
    return sum(len(canal.members) for canal in guild.voice_channels)
