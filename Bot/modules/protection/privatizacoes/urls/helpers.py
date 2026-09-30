from functions.database import database as db

COLLECTION_NAME = "protection_privatizacoes_urls"
CHAVE = "privatizacao_urls"

def carregar_config():
    config = db.get_document(COLLECTION_NAME)
    
    if not config:
        config = {
            CHAVE: {"ativado": False},
            "privatizacao_urls_avancado": {
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
        'none': 'Nenhuma'
    }.get(valor, valor.capitalize())
