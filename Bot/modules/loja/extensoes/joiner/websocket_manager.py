"""
Proxy para o ExtensionsWebSocketManager em connections.
Mantém compatibilidade com o código antigo do módulo joiner.
"""
import logging
from typing import Optional
from connections.extensions_ws import get_extensions_ws

logger = logging.getLogger(__name__)


class BoostWebSocketManager:
    """
    Proxy leve para o ExtensionsWebSocketManager.
    O manager real vive em connections.extensions_ws e é inicializado no on_ready.
    """

    def _get_mgr(self):
        try:
            return get_extensions_ws()
        except ValueError:
            return None

    def set_bot(self, bot):
        pass  # inicializado centralmente

    async def start(self):
        pass  # inicializado centralmente

    async def stop(self):
        pass

    def is_connected(self) -> bool:
        mgr = self._get_mgr()
        return mgr.is_connected() if mgr else False

    def on(self, event: str):
        def decorator(func):
            mgr = self._get_mgr()
            if mgr:
                mgr.on(event)(func)
            return func
        return decorator

    async def request(self, event: str, data: dict, timeout: float = 30.0) -> dict:
        mgr = self._get_mgr()
        return await mgr.request(event, data, timeout) if mgr else {'success': False, 'message': 'Não conectado'}

    async def create_gift(self, gift_data: dict) -> dict:
        mgr = self._get_mgr()
        return await mgr.create_gift(gift_data) if mgr else {'success': False, 'message': 'Não conectado'}

    async def get_gifts(self) -> dict:
        mgr = self._get_mgr()
        return await mgr.get_gifts() if mgr else {'success': False, 'message': 'Não conectado'}

    async def update_gift(self, gift_id: str, gift_data: dict) -> dict:
        mgr = self._get_mgr()
        return await mgr.update_gift(gift_id, gift_data) if mgr else {'success': False, 'message': 'Não conectado'}

    async def delete_gift(self, gift_id: str) -> dict:
        mgr = self._get_mgr()
        return await mgr.delete_gift(gift_id) if mgr else {'success': False, 'message': 'Não conectado'}

    async def delete_all_gifts(self) -> dict:
        mgr = self._get_mgr()
        return await mgr.delete_all_gifts() if mgr else {'success': False, 'message': 'Não conectado'}

    async def run_boost(self, gift_id: str, guild_id: str) -> dict:
        mgr = self._get_mgr()
        return await mgr.run_boost(gift_id, guild_id) if mgr else {'success': False, 'message': 'Não conectado'}

    def get_connection_info(self) -> dict:
        mgr = self._get_mgr()
        return mgr.get_connection_info() if mgr else {'connected': False}


# Singleton
_instance: Optional[BoostWebSocketManager] = None

def get_websocket_manager() -> BoostWebSocketManager:
    global _instance
    if _instance is None:
        _instance = BoostWebSocketManager()
    return _instance
