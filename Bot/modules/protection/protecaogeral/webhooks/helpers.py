from functions.database import database as db

COLLECTION_NAME = "protection_protecaogeral_webhooks"
CHAVE = "webhooks"

def carregar_config():
    config = db.get_document(COLLECTION_NAME)
    
    config_changed = False

    if CHAVE not in config:
        config[CHAVE] = {"limite": 2, "intervalo": 5, "ativado": True}
        config_changed = True

    if "webhooks_avancado" not in config:
        config["webhooks_avancado"] = {"punicao": "ban", "cargos_imunes": [], "canal_logs": None}
        config_changed = True
    
    if config_changed:
        db.save_document(COLLECTION_NAME, {}, config)

    return config

def salvar_config(data):
    db.save_document(COLLECTION_NAME, {}, data)

def formatar_punicao(valor):
    return {
        'ban': 'Banimento',
        'kick': 'Expulsão',
        'timeout_30d': 'Castigo de 30 dias',
        'remove_roles': 'Remoção dos Cargos',
        'none': 'Nenhuma'
    }.get(valor, valor.capitalize())
