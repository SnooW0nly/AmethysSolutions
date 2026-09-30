"""
Hybrid Connection Manager
Uses SocketIOManager as primary (handles WebSocket + HTTP Long-Polling automatically).
Falls back to pure HTTP Polling if Socket.IO also fails.

The old WSManager used raw websockets which cannot talk to a Socket.IO server
(server rejects with HTTP 200 instead of 101 Switching Protocols).
SocketIOManager already handles the Socket.IO handshake and transparently
falls back to HTTP long-polling on its own, so the WSManager layer is no
longer needed.
"""
import asyncio
import logging
from typing import Optional

from .socketio_manager import SocketIOManager
from .http_polling import HTTPPollingManager

logger = logging.getLogger(__name__)


class HybridConnectionManager:
    """
    Manages connection using SocketIOManager (WebSocket + HTTP Long-Polling)
    with a pure HTTP Polling safety net.
    Configurable via configs/config_websocket.json.
    """

    def __init__(self, bot):
        self.bot = bot
        self.socketio_manager = SocketIOManager(bot)
        self.polling_manager  = HTTPPollingManager(bot)
        self.active_manager   = None
        self.connection_mode  = None   # 'socketio' or 'http'

        # Defaults — overridden by config_socket.json if present
        self.use_socketio    = True
        self.max_sio_retries = 2
        self.http_fallback   = True

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def _load_socket_config(self):
        """Load configuration from configs/config_socket.json (optional)."""
        import json, os

        config_path = os.path.join(
            os.path.dirname(__file__), '..', 'configs', 'config_socket.json'
        )

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # Accept both old key names (websocket) and new ones (socketio)
            self.use_socketio    = config.get('socketio', config.get('websocket', True))
            self.max_sio_retries = config.get('max_sio_retries', config.get('max_ws_retries', 2))
            self.http_fallback   = config.get('http_fallback', True)

            print(
                f"📋 [Hybrid] Config loaded: "
                f"socketio={self.use_socketio}, "
                f"max_retries={self.max_sio_retries}, "
                f"fallback={self.http_fallback}"
            )

        except FileNotFoundError:
            print("⚠️ [Hybrid] config_socket.json not found, using defaults")
        except Exception as e:
            print(f"⚠️ [Hybrid] Error loading config: {e}")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def initialize(self):
        """Initialize managers and establish a connection."""
        self._load_socket_config()

        await self.socketio_manager.initialize()
        await self.polling_manager.initialize()

        if not self.use_socketio:
            print("🔧 [Hybrid] Socket.IO disabled in config, using HTTP directly")
            if await self._connect_http():
                return
            print("❌ [Hybrid] HTTP connection also failed!")
            return

        # SocketIOManager handles its own connect internally (via asyncio.create_task)
        # so we just check after a short window whether it managed to connect.
        print(
            f"🔄 [Hybrid] Waiting for Socket.IO connection "
            f"(up to {self.max_sio_retries * 10}s)…"
        )

        for attempt in range(1, self.max_sio_retries + 1):
            print(f"🔄 [Hybrid] Socket.IO check {attempt}/{self.max_sio_retries}…")

            try:
                await asyncio.wait_for(self._wait_for_sio(), timeout=10.0)
            except asyncio.TimeoutError:
                print(f"⏱️ [Hybrid] Socket.IO not ready after attempt {attempt}")

            if self.socketio_manager.is_connected():
                self.active_manager  = self.socketio_manager
                self.connection_mode = 'socketio'
                print("✅ [Hybrid] Using Socket.IO connection")
                return

            if attempt < self.max_sio_retries:
                await asyncio.sleep(1)

        # Fall back to pure HTTP polling
        if self.http_fallback:
            print("🔄 [Hybrid] Falling back to HTTP Polling…")
            if await self._connect_http():
                return

        print("❌ [Hybrid] All connection methods failed!")

    async def _wait_for_sio(self):
        """Poll until Socket.IO reports connected or the caller times out."""
        while not self.socketio_manager.is_connected():
            await asyncio.sleep(0.2)

    async def _connect_http(self) -> bool:
        """Attempt to connect via pure HTTP Polling."""
        if await self.polling_manager.connect():
            self.active_manager  = self.polling_manager
            self.connection_mode = 'http'
            print("✅ [Hybrid] Using HTTP Polling connection")
            return True
        return False

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------

    def is_connected(self) -> bool:
        if self.active_manager:
            return self.active_manager.is_connected()
        return False

    def get_connection_mode(self) -> Optional[str]:
        return self.connection_mode

    # ------------------------------------------------------------------
    # Proxy — all calls are forwarded to whichever manager is active
    # ------------------------------------------------------------------

    async def send(self, event: str, data: dict, request_id: str = None):
        if self.active_manager:
            return await self.active_manager.send(event, data, request_id)
        return False

    async def request(self, event: str, data: dict, timeout: float = 30.0) -> dict:
        if self.active_manager:
            return await self.active_manager.request(event, data, timeout)
        return {'success': False, 'message': 'Not connected'}

    async def disconnect(self):
        if self.active_manager:
            await self.active_manager.disconnect()

    # ------------------------------------------------------------------
    # API Methods (mirrors ws_manager / socketio_manager interface)
    # ------------------------------------------------------------------

    async def register_bot(self, main_bot_id: str, token: str, client_secret: str, client_id: str) -> dict:
        if self.active_manager:
            return await self.active_manager.register_bot(main_bot_id, token, client_secret, client_id)
        return {'success': False, 'message': 'Not connected'}

    async def synchronize(self, bot_id: str, sync_data: dict = None) -> dict:
        if self.active_manager:
            return await self.active_manager.synchronize(bot_id, sync_data)
        return {'success': False, 'message': 'Not connected'}

    async def get_gifts(self, bot_id: str) -> dict:
        if self.active_manager:
            return await self.active_manager.get_gifts(bot_id)
        return {'success': False, 'message': 'Not connected'}

    async def create_gift(self, bot_id: str, gift_data: dict) -> dict:
        if self.active_manager:
            return await self.active_manager.create_gift(bot_id, gift_data)
        return {'success': False, 'message': 'Not connected'}

    async def delete_gift(self, gift_id: str) -> dict:
        if self.active_manager:
            return await self.active_manager.delete_gift(gift_id)
        return {'success': False, 'message': 'Not connected'}

    async def update_definitions(self, definitions: dict) -> dict:
        if self.active_manager:
            return await self.active_manager.update_definitions(definitions)
        return {'success': False, 'message': 'Not connected'}

    async def check_user_verification(self, bot_id: str, user_id: str) -> dict:
        if self.active_manager:
            return await self.active_manager.check_user_verification(bot_id, user_id)
        return {'success': False, 'message': 'Not connected'}

    async def list_members(self, bot_id: str) -> dict:
        if self.active_manager:
            return await self.active_manager.list_members(bot_id)
        return {'success': False, 'message': 'Not connected'}

    async def check_auth_count(self, bot_id: str) -> dict:
        if self.active_manager:
            return await self.active_manager.check_auth_count(bot_id)
        return {'success': False, 'message': 'Not connected'}

    async def recover_data(self, bot_id: str) -> dict:
        if self.active_manager:
            return await self.active_manager.recover_data(bot_id)
        return {'success': False, 'message': 'Not connected'}