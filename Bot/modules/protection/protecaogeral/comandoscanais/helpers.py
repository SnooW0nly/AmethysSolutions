from functions.database import database as db

COLLECTION_NAME = "protection_protecaogeral_comandoscanais"
CHAVE = "comandos_canais"

def carregar_config():
    config = db.get_document(COLLECTION_NAME)

    config_changed = False

    if CHAVE not in config:
        config[CHAVE] = {"ativado": False}
        config_changed = True

    if "comandos_canais_avancado" not in config:
        config["comandos_canais_avancado"] = {
            "cargos_imunes": [],
            "canal_logs": None
        }
        config_changed = True

    if config_changed:
        db.save_document(COLLECTION_NAME, {}, config)

    return config

def salvar_config(data):
    db.save_document(COLLECTION_NAME, {}, data)