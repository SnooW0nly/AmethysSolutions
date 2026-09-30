"""
Cache de tickets_data com TTL curto e write-through.
Evita um hit no MongoDB a cada mensagem recebida num ticket.
"""
import time
import threading
import copy
from typing import Optional

_cache_data: Optional[dict] = None
_cache_time: float = 0.0
_TTL: float = 5.0          # segundos — curto pois tickets_data muda com frequência
_lock = threading.Lock()


def get(db) -> dict:
    """
    Retorna tickets_data do cache. Se expirado, busca no MongoDB e atualiza.
    `db` é a classe database importada pelo caller.
    """
    global _cache_data, _cache_time
    now = time.monotonic()
    with _lock:
        if _cache_data is not None and (now - _cache_time) < _TTL:
            return _cache_data
    # Busca fora do lock para não bloquear outras threads durante I/O
    fresh = db.get_document("tickets_data") or {}
    with _lock:
        _cache_data = fresh
        _cache_time = time.monotonic()
    return fresh


def save(db, data: dict) -> None:
    """Salva no MongoDB e atualiza o cache."""
    global _cache_data, _cache_time
    db.save_document("tickets_data", data)
    with _lock:
        _cache_data = data
        _cache_time = time.monotonic()


def invalidate() -> None:
    """Força expiração do cache na próxima leitura."""
    global _cache_time
    with _lock:
        _cache_time = 0.0