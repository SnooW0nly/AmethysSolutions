from functions.database import database as db

COLLECTION_NAME = "protection_protecaogeral_comandosext"
CHAVE = "comandosext"

def carregar_config():
    config = db.get_document(COLLECTION_NAME)
    
    config_changed = False
    
    if CHAVE not in config:
        config[CHAVE] = {"limite": 5, "intervalo": 15, "ativado": False}
        config_changed = True
        
    if "comandosext_avancado" not in config:
        config["comandosext_avancado"] = {"punicao": "none", "bots_permitidos": [], "canal_logs": None}
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
        'remover_cargos': 'Remoção dos Cargos',
        'none': 'Nenhuma'
    }.get(valor, valor.capitalize())
