import base64
from functions.database import database as db


def carregar_config() -> dict:
    """Carrega a configuração do MongoDB."""
    return db.get_document("automations_cont_feedbacks") or {"ativado": False, "contadores": [], "estilo": 0}


def salvar_config(data: dict) -> None:
    """Salva a configuração no MongoDB."""
    db.save_document("automations_cont_feedbacks", {}, data)


def sanitizar_prefixo(prefixo: str) -> str:
    """Remove caracteres inválidos do prefixo que não podem estar em nomes de canais/categorias."""
    caracteres_invalidos = ['/', '\\', '<', '>', ':', '*', '?', '"', '|']
    prefixo_sanitizado = prefixo
    for char in caracteres_invalidos:
        prefixo_sanitizado = prefixo_sanitizado.replace(char, '')
    prefixo_sanitizado = ' '.join(prefixo_sanitizado.split())
    return prefixo_sanitizado[:50]


def codificar_prefixo(prefixo: str) -> str:
    """Codifica o prefixo em base64 para uso seguro em custom_id."""
    return base64.urlsafe_b64encode(prefixo.encode('utf-8')).decode('utf-8')


def decodificar_prefixo(prefixo_codificado: str) -> str:
    """Decodifica o prefixo de base64."""
    try:
        return base64.urlsafe_b64decode(prefixo_codificado.encode('utf-8')).decode('utf-8')
    except Exception:
        return prefixo_codificado


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


async def contar_mensagens_feedback(bot) -> int:
    """Conta as mensagens no canal de feedbacks configurado."""
    canais_config = db.get_document("canais") or {}
    canal_feedback_id = canais_config.get("canal_de_feedback")
    if not canal_feedback_id:
        return 0
    try:
        canal = await bot.fetch_channel(int(canal_feedback_id))
        count = 0
        async for _ in canal.history(limit=None):
            count += 1
        return count
    except Exception as e:
        print(f"[ContFeedbacks] Erro ao contar mensagens: {e}")
        return 0