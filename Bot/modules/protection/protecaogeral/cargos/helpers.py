from functions.database import database as db

COLLECTION_NAME = "protection_protecaogeral_cargos"
TIPOS = ["criacao", "edicao", "exclusao"]
PADROES = {
    "criacao": {"limite": 3, "intervalo": 10, "ativado": False},
    "edicao": {"limite": 5, "intervalo": 15, "ativado": False},
    "exclusao": {"limite": 2, "intervalo": 5, "ativado": False},
}

def carregar_config():
    config = db.get_document(COLLECTION_NAME)
    
    # Se o documento não existir, config será um dicionário vazio.
    # A lógica abaixo irá popular com os padrões e salvar um novo documento.
    
    config_changed = False
    
    # Initialize main protection types
    for tipo, padrao in PADROES.items():
        if tipo not in config or not all(k in config.get(tipo, {}) for k in padrao):
            config[tipo] = {**padrao, **config.get(tipo, {})}
            config_changed = True

    # Initialize advanced settings
    if "cargos_avancado" not in config:
        config["cargos_avancado"] = {
            "punicao": "none",
            "cargos_imunes": [],
            "canal_logs": None
        }
        config_changed = True
    
    # Save back to ensure file is created with defaults if it was missing/incomplete
    if config_changed:
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
