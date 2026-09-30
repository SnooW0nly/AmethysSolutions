from functions.database import database as db
import uuid
import secrets
import string
from datetime import datetime, timedelta
import pytz

TIMEZONE = pytz.timezone("America/Sao_Paulo")


# ──────────────────────────────────────────
#  CONFIG GERAL
# ──────────────────────────────────────────

def carregar_config() -> dict:
    dados = db.get_document("automations_keys") or {}
    dados.setdefault("ativado", False)
    dados.setdefault("canal_resgate", None)
    dados.setdefault("canal_logs", None)
    dados.setdefault("cargo_resgate", None)
    dados.setdefault("apagar_tentativas", True)
    dados.setdefault("keys", {})
    return dados


def salvar_config(data: dict) -> None:
    db.save_document("automations_keys", {}, data)


# ──────────────────────────────────────────
#  KEYS — CRUD
# ──────────────────────────────────────────

def _gerar_key_str(prefixo: str, sufixo: str, tamanho: int) -> str:
    chars = string.ascii_uppercase + string.digits
    corpo = "".join(secrets.choice(chars) for _ in range(tamanho))
    partes = [corpo[i:i+4] for i in range(0, tamanho, 4)]
    return f"{prefixo}-{'-'.join(partes)}-{sufixo}"


def criar_keys(
    quantidade: int,
    prefixo: str = "KEY",
    sufixo: str = "Subs",
    usos_maximos: int = 1,
    expira_em_horas: int = None,
    categoria: str = "default",
    criado_por: str = "sistema",
) -> list[str]:
    config = carregar_config()
    agora = datetime.now(TIMEZONE).isoformat()
    expiracao = None
    if expira_em_horas:
        expiracao = (datetime.now(TIMEZONE) + timedelta(hours=expira_em_horas)).isoformat()

    novas = []
    tentativas = 0
    while len(novas) < quantidade and tentativas < quantidade * 10:
        tentativas += 1
        key_str = _gerar_key_str(prefixo=prefixo, sufixo=sufixo, tamanho=16)
        if key_str in config["keys"]:
            continue
        config["keys"][key_str] = {
            "criada_em": agora,
            "expiracao": expiracao,
            "usos_maximos": usos_maximos,
            "usos_realizados": 0,
            "categoria": categoria,
            "criado_por": criado_por,
            "resgatada_por": [],
            "ativa": True,
        }
        novas.append(key_str)

    salvar_config(config)
    return novas


def validar_key(key_str: str) -> tuple[bool, str]:
    """Retorna (valida, motivo). motivo: 'ok' | 'nao_encontrada' | 'inativa' | 'expirada' | 'limite_atingido'"""
    config = carregar_config()
    meta = config["keys"].get(key_str)

    if not meta:
        return False, "nao_encontrada"
    if not meta.get("ativa", True):
        return False, "inativa"
    if meta.get("expiracao"):
        exp = datetime.fromisoformat(meta["expiracao"]).astimezone(TIMEZONE)
        if datetime.now(TIMEZONE) > exp:
            return False, "expirada"
    if meta.get("usos_maximos", 1) != -1:
        if meta.get("usos_realizados", 0) >= meta.get("usos_maximos", 1):
            return False, "limite_atingido"
    return True, "ok"


def resgatar_key(key_str: str, user_id: str) -> tuple[bool, str]:
    """Tenta resgatar a key. Retorna (sucesso, motivo)."""
    valida, motivo = validar_key(key_str)
    if not valida:
        return False, motivo

    config = carregar_config()
    meta = config["keys"][key_str]

    if user_id in meta.get("resgatada_por", []):
        return False, "ja_resgatada"

    meta["usos_realizados"] = meta.get("usos_realizados", 0) + 1
    meta["resgatada_por"].append(user_id)

    if meta.get("usos_maximos", 1) != -1:
        if meta["usos_realizados"] >= meta["usos_maximos"]:
            meta["ativa"] = False

    salvar_config(config)
    return True, "ok"


def deletar_key(key_str: str) -> bool:
    config = carregar_config()
    if key_str in config["keys"]:
        del config["keys"][key_str]
        salvar_config(config)
        return True
    return False


def deletar_keys_expiradas() -> int:
    config = carregar_config()
    agora = datetime.now(TIMEZONE)
    antes = len(config["keys"])
    config["keys"] = {
        k: v for k, v in config["keys"].items()
        if not (v.get("expiracao") and agora > datetime.fromisoformat(v["expiracao"]).astimezone(TIMEZONE))
    }
    salvar_config(config)
    return antes - len(config["keys"])


def resetar_todas_keys() -> int:
    config = carregar_config()
    total = len(config["keys"])
    config["keys"] = {}
    salvar_config(config)
    return total


def estatisticas() -> dict:
    config = carregar_config()
    todas = list(config["keys"].values())
    agora = datetime.now(TIMEZONE)

    total = len(todas)
    ativas = sum(1 for k in todas if k.get("ativa", True))
    expiradas = sum(
        1 for k in todas
        if k.get("expiracao") and agora > datetime.fromisoformat(k["expiracao"]).astimezone(TIMEZONE)
    )
    usadas = sum(1 for k in todas if k.get("usos_realizados", 0) > 0)
    categorias: dict[str, int] = {}
    for k in todas:
        cat = k.get("categoria", "default")
        categorias[cat] = categorias.get(cat, 0) + 1

    return {
        "total": total,
        "ativas": ativas,
        "inativas": total - ativas,
        "expiradas": expiradas,
        "usadas": usadas,
        "disponiveis": ativas - usadas,
        "categorias": categorias,
    }


def listar_keys(apenas_ativas: bool = False) -> list[tuple[str, dict]]:
    config = carregar_config()
    resultado = []
    for key_str, meta in config["keys"].items():
        if apenas_ativas and not meta.get("ativa", True):
            continue
        resultado.append((key_str, meta))
    return resultado