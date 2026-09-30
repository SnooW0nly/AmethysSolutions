from functions.database import database as db

DB_PATH = "database/automations/forms.json"

def carregar_config() -> dict:
    """Carrega a configuração dos formulários do arquivo JSON."""
    return db.obter(DB_PATH) or {"ativado": False, "forms": {}}

def salvar_config(data: dict) -> None:
    """Salva a configuração dos formulários no arquivo JSON."""
    db.salvar(DB_PATH, data)
