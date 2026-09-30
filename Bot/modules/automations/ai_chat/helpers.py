from functions.database import database as db
from functions.ai_api import chamar_ia

# Função chamar_ia agora importada de functions.ai_api

def carregar_config() -> dict:
    """Carrega a configuração do banco de dados, definindo valores padrão se necessário."""
    data = db.get_document("automations_ai_chat") or {}
    if "ativado" not in data:
        data["ativado"] = False
    if "chats" not in data:
        data["chats"] = {}
    if "cargo_imune_id" not in data:
        data["cargo_imune_id"] = None
    return data

def salvar_config(data: dict) -> None:
    """Salva a configuração no banco de dados."""
    config_atual = carregar_config()
    config_atual.update(data)
    db.save_document("automations_ai_chat", {}, config_atual)
