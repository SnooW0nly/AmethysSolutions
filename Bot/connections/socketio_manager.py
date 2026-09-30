"""
Socket.IO Manager for Vision Bot
Uses python-socketio with automatic WebSocket + HTTP Long-Polling fallback
"""
import asyncio
import json
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import uuid

import socketio

logger = logging.getLogger(__name__)


class SocketIOManager:
    """Socket.IO Manager with automatic WebSocket + Polling fallback"""
    
    def __init__(self, bot):
        self.bot = bot
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=0,  # Infinite
            reconnection_delay=1,
            reconnection_delay_max=30,
            logger=False,
            engineio_logger=False
        )
        self.connected = False
        
        # Configuration
        self.server_url = None
        self.jwt_secret = None
        self.bot_id = None
        
        # Event handlers
        self.handlers: Dict[str, Callable] = {}
        
        # Pending requests for request-response pattern
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
        logger.info("SocketIOManager initialized")
    
    async def initialize(self):
        """Initialize the Socket.IO manager"""
        try:
            config = self._load_config()
            
            # Cloud Data from database/cloud/data.json (prioritized)
            cloud_data = {}
            try:
                from functions.database import database as db
                cloud_data = db.get_document('cloud_data') or {}
                if not cloud_data:
                    with open('database/cloud/data.json', 'r', encoding='utf-8') as f:
                        cloud_data = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cloud_data: {e}")

            ws_config = config.get('websocket_manager', {}) or config.get('websocket_cloud', {})
            
            # Prioritize server_url from config
            try:
                from modules.cloud.cloud_config import get_cloud_url
                self.server_url = get_cloud_url()
            except Exception:
                self.server_url = cloud_data.get('server_url') or ws_config.get('server_url', 'https://cloud.amethys.app')
            
            # Ensure HTTP/HTTPS (Socket.IO will handle ws/wss internally)
            if self.server_url.startswith('ws://'):
                self.server_url = 'http://' + self.server_url[5:]
            elif self.server_url.startswith('wss://'):
                self.server_url = 'https://' + self.server_url[6:]
            
            self.jwt_secret = ws_config.get('jwt_secret', 'zynx_secret_key')
            
            # Prioritize Bot ID from cloud_data
            bot_config = config.get('bot', {})
            self.bot_id = cloud_data.get('client_id') or bot_config.get('botID', 'SyncBot')
            
            # Register Socket.IO event handlers
            self._register_socketio_handlers()
            
            # Register default application handlers
            self._register_default_handlers()
            
            # Check if configured
            client_id = cloud_data.get('client_id')
            is_configured = bool(client_id and str(client_id).strip())
            
            if ws_config.get('auto_start', True):
                if is_configured:
                    print(f"✅ [SocketIO] Bot configured, starting connection in background...")
                    # Não aguardar a conexão para não travar o bot
                    asyncio.create_task(self.connect())
                else:
                    print("ℹ️ [SocketIO] Bot not configured for Cloud Auth (cloud/data.json is empty)")
                    print("ℹ️ [SocketIO] Connection skipped - bot will run without Cloud features")
            
            logger.info("SocketIOManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SocketIOManager: {e}")
            traceback.print_exc()
    
    def _load_config(self) -> dict:
        """Load configuration from files"""
        config = {}
        
        try:
            with open('configs/config_websocket.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load websocket config: {e}")
        
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config['bot'] = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load main config: {e}")
        
        return config
    
    def _generate_token(self) -> str:
        """Generate JWT token for authentication"""
        try:
            import jwt
            
            discord_id = str(self.bot.user.id) if self.bot and self.bot.user else None
            
            if not discord_id:
                try:
                    with open('config.json', 'r', encoding='utf-8') as f:
                        main_config = json.load(f)
                        discord_id = main_config.get('bot', {}).get('id')
                except:
                    pass

            payload = {
                'botId': str(self.bot_id),
                'discordId': discord_id,
                'exp': datetime.utcnow() + timedelta(hours=24),
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            return token
        except ImportError:
            import base64
            discord_id = str(self.bot.user.id) if self.bot and self.bot.user else None
            if not discord_id:
                try:
                    with open('config.json', 'r', encoding='utf-8') as f:
                        discord_id = json.load(f).get('bot', {}).get('id')
                except: pass

            payload_data = {
                'botId': str(self.bot_id),
                'discordId': discord_id,
            }
            return base64.b64encode(json.dumps(payload_data).encode()).decode()
    
    def _register_socketio_handlers(self):
        """Register Socket.IO connection event handlers"""
        
        @self.sio.event
        async def connect():
            self.connected = True
            transport = self.sio.transport()
            print(f"✅ [SocketIO] Connected! Transport: {transport}")
            logger.info(f"Connected to server using {transport}")
            
            # Send bot info after connection
            await self._send_bot_info()
        
        @self.sio.event
        async def disconnect():
            self.connected = False
            print(f"❌ [SocketIO] Disconnected from server")
            logger.info("Disconnected from server")
        
        @self.sio.event
        async def connect_error(data):
            print(f"⚠️ [SocketIO] Connection error: {data}")
            logger.error(f"Connection error: {data}")
        
        @self.sio.on('connect_failed')
        async def connect_failed(data):
            print(f"❌ [SocketIO] Connection failed: {data}")
            logger.error(f"Connection failed: {data}")
        
        # Catch all events
        @self.sio.on('*')
        async def catch_all(event, data):
            # Ignore error events to avoid duplicate logging
            if event in ['connect_error', 'connect_failed', 'error']:
                return
            
            print(f"📥 [SocketIO] Event: {event}")
            
            # Check for response to pending request
            if event and event.endswith('_response'):
                request_id = data.get('requestId') if isinstance(data, dict) else None
                if request_id and request_id in self.pending_requests:
                    future = self.pending_requests.pop(request_id)
                    if not future.done():
                        print(f"✅ [SocketIO] Resolved request: {request_id[:8]}...")
                        future.set_result(data)
                    return
            
            # Dispatch to application handler
            if event in self.handlers:
                try:
                    asyncio.create_task(self.handlers[event](data))
                except Exception as e:
                    print(f"❌ [SocketIO] Handler error for {event}: {e}")
    
    def _register_default_handlers(self):
        """Register default event handlers"""
        
        @self.on('connected')
        async def on_connected(data):
            print(f"📥 [SocketIO] Welcome message: {data}")
        
        @self.on('auth_log')
        async def on_auth_log(data):
            try:
                from modules.cloud.update_api import process_auth_log
                await process_auth_log(data)
            except ImportError:
                pass
            except Exception as e:
                logger.error(f"Error processing auth_log: {e}")
        
        @self.on('redeem_gift')
        async def on_redeem_gift(data):
            try:
                from .handlers import handle_redeem_gift
                await handle_redeem_gift(self.bot, data)
            except ImportError:
                pass
        
        @self.on('remove_verified_role')
        async def on_remove_role(data):
            try:
                from .handlers import handle_remove_role
                await handle_remove_role(self.bot, data)
            except ImportError:
                pass
    
    def on(self, event: str):
        """Decorator to register event handler"""
        def decorator(func):
            self.handlers[event] = func
            return func
        return decorator
    
    async def connect(self):
        """Connect to Socket.IO server"""
        try:
            token = self._generate_token()
            
            print(f"🔄 [SocketIO] Connecting to {self.server_url}...")
            print(f"🚀 [SocketIO] Transports: WebSocket → HTTP Long-Polling (automatic fallback)")
            
            await self.sio.connect(
                self.server_url,
                auth={'token': token},
                transports=['websocket'],  # polling removed: causes aiohttp ClientWSTimeout on 3.9+
                wait_timeout=10,  # Reduzido para 10s para não travar o bot
            )
            
            # Keep connection alive
            await self.sio.wait()
            
        except asyncio.TimeoutError:
            print(f"⏱️ [SocketIO] Connection timeout - continuing in background")
            logger.warning("Connection timeout")
        except Exception as e:
            print(f"⚠️ [SocketIO] Connection failed: {e}")
            print(f"ℹ️ [SocketIO] Bot will continue without Cloud connection")
            logger.error(f"Connection failed: {e}")
    
    async def _send_bot_info(self):
        """Send bot information after connecting"""
        try:
            # Wait for connection to be fully established
            max_wait = 5  # Wait up to 5 seconds
            for _ in range(max_wait * 10):
                if self.connected and self.sio.connected:
                    break
                await asyncio.sleep(0.1)
            
            if not self.connected:
                logger.warning("Cannot send bot info: not connected")
                return
            
            config = self._load_config()
            bot_config = config.get('bot', {})
            
            guilds = []
            if self.bot.guilds:
                guilds = [str(g.id) for g in self.bot.guilds]
            
            data = {
                'bot_id': str(self.bot.user.id) if self.bot.user else None,
                'unique_id': bot_config.get('botID'),
                'server_id': bot_config.get('bot', {}).get('server'),
                'oauth_client_id': None,
                'guilds': guilds
            }
            
            try:
                from functions.database import database as db
                cloud_config = db.get_document('cloud_data') or {}
                data['oauth_client_id'] = cloud_config.get('client_id')
            except Exception:
                pass
            
            await self.send('bot_connected', data)
            print(f"📤 [SocketIO] Bot info sent ({len(guilds)} guilds)")
            
        except Exception as e:
            logger.error(f"Failed to send bot info: {e}")
    
    async def send(self, event: str, data: dict, request_id: str = None):
        """Send a message to the server"""
        if not self.connected or not self.sio.connected:
            logger.warning(f"Cannot send {event}: not connected")
            return False
        
        try:
            # Socket.IO handles events natively, no need for JSON wrapper
            if request_id:
                data['requestId'] = request_id
            
            await self.sio.emit(event, data)
            return True
        except Exception as e:
            logger.error(f"Failed to send {event}: {e}")
            return False
    
    async def request(self, event: str, data: dict, timeout: float = 30.0) -> dict:
        """Send a request and wait for response"""
        request_id = str(uuid.uuid4())
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        
        future = loop.create_future()
        self.pending_requests[request_id] = future
        
        try:
            # Send request
            success = await self.send(event, data, request_id=request_id)
            if not success:
                self.pending_requests.pop(request_id, None)
                return {'success': False, 'message': 'Failed to send request'}
            
            # Wait for response
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            return {'success': False, 'message': 'Request timeout'}
        except Exception as e:
            self.pending_requests.pop(request_id, None)
            return {'success': False, 'message': str(e)}
    
    async def disconnect(self):
        """Disconnect from server"""
        if self.sio.connected:
            await self.sio.disconnect()
        
        self.connected = False
        logger.info("Disconnected from Socket.IO")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected and self.sio.connected
    
    # ============================================
    # API Methods
    # ============================================
    
    async def register_bot(self, main_bot_id: str, token: str, client_secret: str, client_id: str) -> dict:
        """Register bot with API"""
        return await self.request('register', {
            'mainBotId': main_bot_id,
            'token': token,
            'clientSecret': client_secret,
            'clientId': client_id
        })
    
    async def synchronize(self, bot_id: str, sync_data: dict = None) -> dict:
        """Synchronize data with API"""
        return await self.request('synchronization', {
            'botId': bot_id,
            'syncData': sync_data
        })
    
    async def get_gifts(self, bot_id: str) -> dict:
        """Get gifts for bot"""
        return await self.request('get_gifts', {'botId': bot_id})
    
    async def create_gift(self, bot_id: str, gift_data: dict) -> dict:
        """Create a new gift"""
        return await self.request('create_gift', {
            'botId': bot_id,
            'giftData': gift_data
        })
    
    async def delete_gift(self, gift_id: str) -> dict:
        """Delete a gift"""
        actual_id = gift_id
        if isinstance(gift_id, dict):
            actual_id = gift_id.get('gift_id') or gift_id.get('id')
            
        logger.info(f"🗑️ [SocketIO] Requesting deletion of gift: '{actual_id}'")
        return await self.request('delete_gift', {'giftId': str(actual_id), 'gift_id': str(actual_id)})
    
    async def update_definitions(self, definitions: dict) -> dict:
        """Update bot definitions"""
        config = self._load_config()
        bot_config = config.get('bot', {})
        
        cloud_config = {}
        try:
            from functions.database import database as db
            cloud_config = db.get_document('cloud_data') or {}
        except Exception:
            pass
        
        return await self.request('update_definitions', {
            'bot_id': cloud_config.get('client_id'),
            'definitions': definitions,
            'main_server_id': bot_config.get('bot', {}).get('server')
        })
    
    async def check_user_verification(self, bot_id: str, user_id: str) -> dict:
        """Check if user is verified"""
        return await self.request('check_user_verification', {
            'botId': bot_id,
            'userId': user_id
        })
    
    async def list_members(self, bot_id: str) -> dict:
        """List members for bot"""
        return await self.request('list_members', {'botId': bot_id})
    
    async def check_auth_count(self, bot_id: str) -> dict:
        """Check authenticated member count"""
        return await self.request('check_auth_count', {'botId': bot_id})
    
    async def recover_data(self, bot_id: str) -> dict:
        """Recover bot data"""
        return await self.request('recover', {'botId': bot_id})
    
    # ============================================
    # Backwards Compatibility Methods
    # ============================================
    
    def set_bot(self, bot):
        """Set bot instance"""
        self.bot = bot
    
    async def start(self):
        """Start connection"""
        await self.initialize()
    
    async def stop(self):
        """Stop connection"""
        await self.disconnect()
    
    def set_callbacks(self, on_connect=None, on_disconnect=None, on_error=None, on_message=None):
        """Set callbacks (backwards compatibility - uses event handlers instead)"""
        if on_connect:
            @self.sio.event
            async def connect():
                self.connected = True
                await on_connect()
        
        if on_disconnect:
            @self.sio.event
            async def disconnect():
                self.connected = False
                await on_disconnect()
        
        if on_error:
            @self.sio.event
            async def connect_error(data):
                await on_error(data)
        
        if on_message:
            # Store message callback for dispatching all events
            self._on_message_callback = on_message
    
    async def resend_bot_connected(self):
        """Resend bot_connected event (backwards compatibility)"""
        await self._send_bot_info()
