"""
coins.py — Sistema de moeda interna do ApostadoFF
Mediadores e analistas ganham Coins ao concluir APs.
Admins configuram ganho por AP, multiplicador global e Cargo UPs automáticos.
"""
from functions.database import database as db

# ─── Chaves de DB ──────────────────────────────────────────────────────────────
COINS_KEY     = "apostadoff_coins"       # {uid: {saldo, total_ganho, total_gasto, aps, analises}}
COINS_CFG_KEY = "apostadoff_coins_cfg"   # configurações globais

DEFAULT_CFG: dict = {
    "coins_por_ap_mediador":  10,   # coins ganhos por AP mediado
    "coins_por_ap_analista":   5,   # coins ganhos por análise concluída
    "multiplicador":         1.0,   # multiplicador global (float)
    "nome_moeda":          "Coin",  # nome exibido
    "emoji_moeda":            "🪙",  # emoji exibido
    # Lista de Cargo UPs: [{cargo_id, min_coins_total, min_aps, min_analises, nome_rank}]
    "cargo_ups": [],
}

_DADO_ZERO = {
    "saldo": 0, "total_ganho": 0, "total_gasto": 0,
    "aps": 0, "analises": 0,
}


# ─── Config ────────────────────────────────────────────────────────────────────
def get_cfg() -> dict:
    base = DEFAULT_CFG.copy()
    salvo = db.get_document(COINS_CFG_KEY) or {}
    base.update(salvo)
    return base


def save_cfg(cfg: dict):
    db.save_document(COINS_CFG_KEY, cfg)


# ─── Operações de saldo ────────────────────────────────────────────────────────
def _load() -> dict:
    return db.get_document(COINS_KEY) or {}


def _dump(data: dict):
    db.save_document(COINS_KEY, data)


def get_dados(user_id: str) -> dict:
    return _load().get(str(user_id), _DADO_ZERO.copy())


def add_coins(user_id: str, amount: int, tipo: str = "bonus") -> dict:
    """
    Adiciona coins com multiplicador aplicado.
    tipo: 'ap' | 'analise' | 'bonus'
    Retorna dados atualizados do usuário.
    """
    cfg  = get_cfg()
    mult = float(cfg.get("multiplicador", 1.0))
    real = max(1, round(amount * mult))

    all_d = _load()
    d     = all_d.get(str(user_id), _DADO_ZERO.copy())
    d["saldo"]       = d.get("saldo",       0) + real
    d["total_ganho"] = d.get("total_ganho", 0) + real
    if tipo == "ap":
        d["aps"]      = d.get("aps",      0) + 1
    elif tipo == "analise":
        d["analises"] = d.get("analises", 0) + 1
    all_d[str(user_id)] = d
    _dump(all_d)
    return d


def remove_coins(user_id: str, amount: int) -> bool:
    """Remove coins. Retorna False se saldo insuficiente."""
    all_d = _load()
    d     = all_d.get(str(user_id), _DADO_ZERO.copy())
    if d.get("saldo", 0) < amount:
        return False
    d["saldo"]       -= amount
    d["total_gasto"]  = d.get("total_gasto", 0) + amount
    all_d[str(user_id)] = d
    _dump(all_d)
    return True


def admin_set_coins(user_id: str, novo_saldo: int):
    """Admin: define saldo diretamente (sem afetar total_ganho/gasto)."""
    all_d = _load()
    d     = all_d.get(str(user_id), _DADO_ZERO.copy())
    d["saldo"] = max(0, novo_saldo)
    all_d[str(user_id)] = d
    _dump(all_d)


def get_ranking(top: int = 10) -> list[tuple[str, dict]]:
    """Lista (uid, dados) ordenada por total_ganho desc."""
    all_d = _load()
    ranked = sorted(all_d.items(), key=lambda x: x[1].get("total_ganho", 0), reverse=True)
    return ranked[:top]


# ─── Cargo UP automático ───────────────────────────────────────────────────────
async def verificar_cargo_ups(member, guild) -> list[str]:
    """
    Verifica e aplica cargos UP se o membro atingiu os requisitos.
    Retorna lista de nomes de ranks desbloqueados nesta chamada.
    """
    cfg   = get_cfg()
    dados = get_dados(str(member.id))
    novos: list[str] = []

    total_ganho = dados.get("total_ganho", 0)
    aps         = dados.get("aps",         0)
    analises    = dados.get("analises",    0)

    for up in cfg.get("cargo_ups", []):
        cargo_id      = up.get("cargo_id")
        min_coins     = int(up.get("min_coins_total", 0))
        min_aps       = int(up.get("min_aps",         0))
        min_analises  = int(up.get("min_analises",    0))
        nome_rank     = up.get("nome_rank", "Rank")

        if not cargo_id:
            continue

        role = guild.get_role(int(cargo_id))
        if not role or role in member.roles:
            continue   # já tem o cargo ou cargo não existe

        if min_coins   > 0 and total_ganho < min_coins:
            continue
        if min_aps     > 0 and aps         < min_aps:
            continue
        if min_analises > 0 and analises   < min_analises:
            continue

        try:
            await member.add_roles(role, reason=f"ApostadoFF Cargo UP: {nome_rank}")
            novos.append(nome_rank)
        except Exception:
            pass

    return novos