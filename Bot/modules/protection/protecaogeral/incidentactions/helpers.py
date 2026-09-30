from functions.database import database as db

COLLECTION_NAME = "protection_protecaogeral_incidentactions"
CHAVE = "incident_actions"

# Durações disponíveis (em minutos) e seus labels
DURACOES = {
    "15m":    {"label": "15 minutos",  "minutos": 15},
    "30m":    {"label": "30 minutos",  "minutos": 30},
    "1h":     {"label": "1 hora",      "minutos": 60},
    "3h":     {"label": "3 horas",     "minutos": 180},
    "6h":     {"label": "6 horas",     "minutos": 360},
    "12h":    {"label": "12 horas",    "minutos": 720},
    "1d":     {"label": "1 dia",       "minutos": 1440},
    "3d":     {"label": "3 dias",      "minutos": 4320},
    "7d":     {"label": "7 dias",      "minutos": 10080},
    "24h":    {"label": "24 horas",    "minutos": 1440},
}

# Duração máxima que o Discord aceita para incident actions: 24h = 1440 minutos
DURACAO_MAX_MINUTOS = 1440


def duracao_para_minutos(chave: str) -> int:
    """Converte chave de duração para minutos."""
    entrada = DURACOES.get(chave)
    if not entrada:
        return 60
    return min(entrada["minutos"], DURACAO_MAX_MINUTOS)


def formatar_duracao(chave: str) -> str:
    """Retorna o label legível de uma duração."""
    return DURACOES.get(chave, {}).get("label", chave)


def carregar_config() -> dict:
    config = db.get_document(COLLECTION_NAME)

    changed = False
    if CHAVE not in config:
        config[CHAVE] = {
            "dms_ativado": False,
            "invites_ativado": False,
            "duracao_dms": "1h",
            "duracao_invites": "1h",
        }
        changed = True

    if f"{CHAVE}_avancado" not in config:
        config[f"{CHAVE}_avancado"] = {
            "canal_logs": None,
        }
        changed = True

    if changed:
        db.save_document(COLLECTION_NAME, {}, config)

    return config


def salvar_config(data: dict) -> None:
    db.save_document(COLLECTION_NAME, {}, data)