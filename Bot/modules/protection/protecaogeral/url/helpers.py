from functions.database import database as db

COLLECTION_NAME = "protection_protecaourl"
CHAVE = "protecao_url"

def carregar_config():
    config = db.get_document(COLLECTION_NAME)
    changed = False
    if CHAVE not in config:
        config[CHAVE] = {"ativado": False}
        changed = True
    if f"{CHAVE}_avancado" not in config:
        config[f"{CHAVE}_avancado"] = {
            "url_nome": None,
            "ultima_tentativa": None,
            "canal_logs": None,
            "token_user_id": None,
        }
        changed = True
    if changed:
        db.save_document(COLLECTION_NAME, {}, config)
    return config

def salvar_config(data):
    db.save_document(COLLECTION_NAME, {}, data)