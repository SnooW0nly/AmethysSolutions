from functions.database import database as db

COLLECTION_NAME = "protection_protecaogeral_canais"
TIPOS = ["criacao", "edicao", "exclusao"]
PADROES = {
    "criacao": {"limite": 3, "intervalo": 10, "ativado": False},
    "edicao": {"limite": 5, "intervalo": 15, "ativado": False},
    "exclusao": {"limite": 2, "intervalo": 5, "ativado": False},
}

def carregar_config():
    config = db.get_document(COLLECTION_NAME)
    
    if not config:
        config = {
            **PADROES,
            "canais_avancado": {
                "punicao": "none",
                "cargos_imunes": [],
                "categorias_imunes": [],
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
        'remover_cargos': 'Remoção de Cargos',
        'revert_action': 'Reversão da Ação',
        'timeout_30d': 'Castigo de 30 dias',
        'none': 'Nenhuma'
    }.get(valor, valor.capitalize())
