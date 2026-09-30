from functions.database import database as db
import disnake

def carregar_config() -> dict:
    """Carrega a configuração da coleção 'lock_unlock'."""
    dados = db.get_document("automations_lock_unlock") or {}
    if not isinstance(dados, dict):
        dados = {}
    dados.setdefault("ativado", False)
    dados.setdefault("canais", {})
    dados.setdefault("logs_ativados", False)
    return dados

def salvar_config(data: dict) -> None:
    """Salva a configuração na coleção 'lock_unlock'."""
    db.save_document("automations_lock_unlock", {}, data)

async def obter_canal_logs(bot: disnake.Client) -> disnake.TextChannel | None:
    try:
        canais_config = db.get_document("canais") or {}
        canal_logs_id = canais_config.get("canal_de_logs_do_sistema")
        if canal_logs_id:
            canal = bot.get_channel(int(canal_logs_id))
            if isinstance(canal, disnake.TextChannel):
                return canal
    except Exception:
        pass
    return None
