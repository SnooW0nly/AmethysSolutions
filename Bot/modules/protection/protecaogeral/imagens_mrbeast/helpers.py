from functions.database import database as db

COLLECTION_NAME = "protection_protecaogeral_imagensmrbeast"
CHAVE = "imagens_mrbeast"


def carregar_config() -> dict:
    config = db.get_document(COLLECTION_NAME)

    changed = False
    if CHAVE not in config:
        config[CHAVE] = {
            "ativado": False,
        }
        changed = True

    if f"{CHAVE}_avancado" not in config:
        config[f"{CHAVE}_avancado"] = {
            "punicao": "ban",
            "cargos_imunes": [],
            "canal_logs": None,
            "limite": 1,
            "intervalo": 60,
        }
        changed = True

    if changed:
        db.save_document(COLLECTION_NAME, {}, config)

    return config


def salvar_config(data: dict) -> None:
    db.save_document(COLLECTION_NAME, {}, data)


def formatar_punicao(valor: str) -> str:
    return {
        "ban": "Banir",
        "kick": "Expulsar",
        "remover_cargos": "Remover Cargos",
        "none": "Nenhuma",
    }.get(valor, valor.capitalize())
