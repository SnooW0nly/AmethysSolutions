"""
Gerencia locks por usuário+painel para evitar criação duplicada de tickets
em condições de corrida (ex.: cliques rápidos ou multiplos selects).
"""
import asyncio
from typing import Dict

_locks: Dict[str, asyncio.Lock] = {}
_meta_lock = asyncio.Lock()


async def acquire(panel_id: str, user_id: int) -> asyncio.Lock:
    """
    Retorna (e adquire) o lock para (panel_id, user_id).
    Use com `async with ticket_locks.acquire(...) as lock:` — veja get_lock().
    """
    key = f"{panel_id}:{user_id}"
    async with _meta_lock:
        if key not in _locks:
            _locks[key] = asyncio.Lock()
        lock = _locks[key]
    return lock


class _TicketLock:
    def __init__(self, panel_id: str, user_id: int):
        self._key = f"{panel_id}:{user_id}"
        self._lock: asyncio.Lock | None = None

    async def __aenter__(self):
        async with _meta_lock:
            if self._key not in _locks:
                _locks[self._key] = asyncio.Lock()
            self._lock = _locks[self._key]
        await self._lock.acquire()
        return self

    async def __aexit__(self, *args):
        if self._lock:
            self._lock.release()


def for_user(panel_id: str, user_id: int) -> _TicketLock:
    """
    Uso:
        async with ticket_locks.for_user(panel_id, user.id):
            # criação do ticket aqui
    """
    return _TicketLock(panel_id, user_id)