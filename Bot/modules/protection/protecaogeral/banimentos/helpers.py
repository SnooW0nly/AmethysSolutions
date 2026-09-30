from functions.database import database as db

COLLECTION_NAME = "protection_protecaogeral_banimentos"
CHAVE = "banimento"

def carregar_config():
    config = db.get_document(COLLECTION_NAME)
    
    if not config:
        config = {
            CHAVE: {"limite": 2, "intervalo": 10, "ativado": False},
            "banimentos_avancado": {
                "punicao": "none", 
                "cargos_imunes": [], 
                "canal_logs": None
            }
        }
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
        'revert_action': 'Reversão da Ação',
        'none': 'Nenhuma'
    }.get(valor, valor.capitalize())
