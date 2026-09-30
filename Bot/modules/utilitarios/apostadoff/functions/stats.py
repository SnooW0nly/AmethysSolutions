from functions.database import database as db

APOSTADOFF_STATS_KEY = "apostadoff_stats"

async def adicionar_vitoria(user_id: str, pontos: int):
    stats = db.get_document(APOSTADOFF_STATS_KEY) or {}
    user = stats.get(user_id, {"vitorias":0, "derrotas":0, "pontos":0, "partidas":0})
    user["vitorias"] += 1
    user["pontos"] += pontos
    user["partidas"] += 1
    stats[user_id] = user
    db.save_document(APOSTADOFF_STATS_KEY, stats)

async def adicionar_derrota(user_id: str):
    stats = db.get_document(APOSTADOFF_STATS_KEY) or {}
    user = stats.get(user_id, {"vitorias":0, "derrotas":0, "pontos":0, "partidas":0})
    user["derrotas"] += 1
    user["partidas"] += 1
    stats[user_id] = user
    db.save_document(APOSTADOFF_STATS_KEY, stats)