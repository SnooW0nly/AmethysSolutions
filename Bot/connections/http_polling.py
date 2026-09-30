"""
HTTP Polling fallback for WebSocket
Works when WebSocket is blocked or unavailable
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class HTTPPollingManager:
    """HTTP Polling Manager - fallback for WebSocket"""
    
    def __init__(self, bot):
        self.bot = bot
        self.connected = False
        self.should_poll = True
        self.poll_interval = 2  # Poll every 2 seconds
        
        # Configuration
        self.server_url = None
        self.bot_id = None
        
        # Event handlers
        self.handlers: Dict[str, Callable] = {}
        
        # Tasks
        self._poll_task = None
        
        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        
        logger.info("HTTPPollingManager initialized")
    
    def set_bot(self, bot):
        """Set bot instance (compatibility with SocketIOManager)"""
        self.bot = bot
        if bot and bot.user:
            self.bot_id = str(bot.user.id)
    
    def set_callbacks(self, on_connect=None, on_disconnect=None, on_error=None, on_message=None):
        """Set event callbacks (compatibility with SocketIOManager)"""
        if on_connect:
            self.handlers['connect'] = on_connect
        if on_disconnect:
            self.handlers['disconnect'] = on_disconnect
        if on_error:
            self.handlers['error'] = on_error
        if on_message:
            self.handlers['message'] = on_message
    
    async def initialize(self):
        """Initialize the HTTP Polling manager"""
        try:
            import json
            
            # Load configuration
            with open('configs/config_websocket.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            ws_config = config.get('websocket_manager', {}) or config.get('websocket_cloud', {})
            
            # Get server URL
            try:
                from modules.cloud.cloud_config import get_cloud_url
                self.server_url = get_cloud_url()
            except Exception:
                self.server_url = ws_config.get('server_url', 'https://cloud.zenityapplications.com.br')
            
            # Remove ws:// or wss:// and replace with http:// or https://
            if self.server_url.startswith('ws://'):
                self.server_url = 'http://' + self.server_url[5:]
            elif self.server_url.startswith('wss://'):
                self.server_url = 'https://' + self.server_url[6:]
            
            # Get bot ID
            try:
                from functions.database import database as db
                cloud_data = db.get_document('cloud_data') or {}
                self.bot_id = cloud_data.get('client_id')
            except Exception:
                pass
            
            if not self.bot_id:
                with open('config.json', 'r', encoding='utf-8') as f:
                    main_config = json.load(f)
                    self.bot_id = main_config.get('bot', {}).get('botID', 'VisionBot')
            
            # Register default handlers
            self._register_default_handlers()
            
            logger.info("HTTPPollingManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize HTTPPollingManager: {e}")
    
    def _register_default_handlers(self):
        """Register default event handlers"""
        
        @self.on('connected')
        async def on_connected(data):
            logger.info(f"✅ Connected via HTTP Polling: {data.get('message')}")
        
        @self.on('auth_log')
        async def on_auth_log(data):
            try:
                from modules.cloud.update_api import process_auth_log
                await process_auth_log(data)
            except ImportError:
                pass
        
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
    
    def _get_http_endpoint(self, event: str) -> str:
        """Map WebSocket event to HTTP endpoint"""
        event_map = {
            'bot_connected': '/api/bot/connect',
            'register': '/api/bot/register',
            'update_definitions': '/api/bot/definitions',
            'synchronization': '/api/bot/sync',
            'get_gifts': '/api/gifts',
            'create_gift': '/api/gifts',
            'delete_gift': '/api/gifts',
            'list_members': '/api/members',
            'check_auth_count': '/api/auth/count',
            'check_user_verification': '/api/user/verification',
            'recover': '/api/bot/recover',
            'refresh_token': '/api/token/refresh',
            # Novas rotas
            'recover_members': '/api/members/recover',
            'remove_verified_role': '/api/role/remove',
            'redeem_gift': '/api/gift/redeem',
        }
        return event_map.get(event, f'/api/{event}')
    
    def _get_http_method(self, event: str) -> str:
        """Get HTTP method for event"""
        get_events = ['get_gifts', 'list_members', 'check_auth_count', 'check_user_verification', 'recover']
        delete_events = ['delete_gift']
        put_events = ['update_definitions']
        
        if event in get_events:
            return 'GET'
        elif event in delete_events:
            return 'DELETE'
        elif event in put_events:
            return 'PUT'
        return 'POST'
    
    def _build_payload(self, event: str, data: dict) -> dict:
        """Build payload for HTTP request"""
        # Add botId if not present
        if 'botId' not in data and 'bot_id' not in data:
            data['botId'] = str(self.bot.user.id) if self.bot and self.bot.user else self.bot_id
        return data
    
    async def connect(self):
        """Connect via HTTP Polling"""
        try:
            print(f"🔄 [HTTP Polling] Starting connection...")
            print(f"🌐 [HTTP Polling] Server: {self.server_url}")
            
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Get oauth_client_id from cloud_data
            oauth_client_id = None
            try:
                from functions.database import database as db
                cloud_data = db.get_document('cloud_data') or {}
                oauth_client_id = cloud_data.get('client_id')
            except:
                pass
            
            # Send connect request
            async with self.session.post(
                f"{self.server_url}/api/bot/connect",
                json={
                    'bot_id': str(self.bot.user.id) if self.bot and self.bot.user else self.bot_id,
                    'unique_id': str(self.bot.user.id) if self.bot and self.bot.user else self.bot_id,
                    'oauth_client_id': oauth_client_id
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ [HTTP Polling] Connected: {data.get('message')}")
                    self.connected = True
                    
                    # Send bot info
                    await self._send_bot_info()
                    
                    # Start polling loop
                    self._poll_task = asyncio.create_task(self._poll_loop())
                    
                    return True
                else:
                    print(f"❌ [HTTP Polling] Connection failed: {resp.status}")
                    return False
                    
        except Exception as e:
            print(f"❌ [HTTP Polling] Connection error: {e}")
            return False
    
    async def _send_bot_info(self):
        """Send bot information after connecting"""
        try:
            guilds = []
            if self.bot.guilds:
                guilds = [str(g.id) for g in self.bot.guilds]
            
            # Get oauth_client_id from cloud_data
            oauth_client_id = None
            try:
                from functions.database import database as db
                cloud_data = db.get_document('cloud_data') or {}
                oauth_client_id = cloud_data.get('client_id')
            except:
                pass
            
            data = {
                'bot_id': str(self.bot.user.id) if self.bot.user else None,
                'unique_id': self.bot_id,
                'guilds': guilds,
                'oauth_client_id': oauth_client_id
            }
            
            await self.send('bot_connected', data)
            print(f"📤 [HTTP Polling] Bot info sent ({len(guilds)} guilds, client_id: {oauth_client_id})")
            
        except Exception as e:
            logger.error(f"Failed to send bot info: {e}")
    
    async def _poll_loop(self):
        """Poll for messages and auth logs"""
        while self.should_poll and self.connected:
            try:
                # Poll for auth logs
                bot_id = str(self.bot.user.id) if self.bot and self.bot.user else self.bot_id
                
                # Também buscar pelo client_id se disponível
                client_id = None
                try:
                    from functions.database import database as db
                    cloud_data = db.get_document('cloud_data') or {}
                    client_id = cloud_data.get('client_id')
                except:
                    pass
                
                # Buscar auth logs
                try:
                    async with self.session.get(
                        f"{self.server_url}/api/auth/logs",
                        params={'botId': bot_id, 'clientId': client_id},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            logs = data.get('data', {}).get('logs', [])
                            
                            # Process each auth log via message handler
                            for log in logs:
                                user = log.get('user', {})
                                print(f"📝 [HTTP Polling] Auth log recebido: {user.get('username')}")
                                
                                # Usar o handler 'message' com formato {event, data}
                                if 'message' in self.handlers:
                                    try:
                                        await self.handlers['message']({
                                            'event': 'auth_log',
                                            'data': log
                                        })
                                    except Exception as e:
                                        logger.error(f"Auth log handler error: {e}")
                                # Fallback: chamar process_auth_log diretamente
                                else:
                                    try:
                                        from modules.cloud.update_api import process_auth_log
                                        await process_auth_log(log)
                                    except Exception as e:
                                        logger.error(f"Direct auth_log processing error: {e}")
                        elif resp.status != 400:  # 400 é esperado se não houver botId
                            logger.debug(f"Auth logs check returned: {resp.status}")
                except Exception as e:
                    logger.debug(f"Auth logs poll error (ignorando): {e}")
                
                # Health check - opcional, não falha se não existir
                try:
                    async with self.session.get(
                        f"{self.server_url}/health",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            messages = data.get('messages', [])
                            
                            # Process each message
                            for msg in messages:
                                event = msg.get('event')
                                payload = msg.get('data', {})
                                
                                if 'message' in self.handlers:
                                    try:
                                        await self.handlers['message']({'event': event, 'data': payload})
                                    except Exception as e:
                                        logger.error(f"Handler error for {event}: {e}")
                except Exception as e:
                    # Health check é opcional - não logar erro
                    pass
                    
                # Wait before next poll
                await asyncio.sleep(self.poll_interval)
                
            except Exception as e:
                import traceback
                logger.error(f"Poll error: {e}")
                traceback.print_exc()
                await asyncio.sleep(self.poll_interval)
    
    async def send(self, event: str, data: dict):
        """Send a message to the server"""
        if not self.session or not self.connected:
            logger.warning(f"Cannot send {event}: not connected")
            return False
        
        try:
            # Map events to HTTP endpoints
            endpoint = self._get_http_endpoint(event)
            method = self._get_http_method(event)
            payload = self._build_payload(event, data)
            
            if method == 'GET':
                async with self.session.get(
                    f"{self.server_url}{endpoint}",
                    params=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    return resp.status == 200
            else:
                async with self.session.post(
                    f"{self.server_url}{endpoint}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        return True
                    else:
                        logger.error(f"Failed to send {event}: {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"Failed to send {event}: {e}")
            return False
    
    async def request(self, event: str, data: dict, timeout: float = 30.0) -> dict:
        """Send a request and get response"""
        if not self.session or not self.connected:
            return {'success': False, 'message': 'Not connected'}
        
        try:
            endpoint = self._get_http_endpoint(event)
            method = self._get_http_method(event)
            payload = self._build_payload(event, data)
            
            if method == 'GET':
                async with self.session.get(
                    f"{self.server_url}{endpoint}",
                    params=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {'success': False, 'message': f'HTTP {resp.status}'}
            elif method == 'DELETE':
                # For delete, extract ID from payload
                gift_id = payload.get('gift_id') or payload.get('giftId') or payload.get('id')
                async with self.session.delete(
                    f"{self.server_url}{endpoint}/{gift_id}",
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {'success': False, 'message': f'HTTP {resp.status}'}
            elif method == 'PUT':
                async with self.session.put(
                    f"{self.server_url}{endpoint}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {'success': False, 'message': f'HTTP {resp.status}'}
            else:  # POST
                async with self.session.post(
                    f"{self.server_url}{endpoint}",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {'success': False, 'message': f'HTTP {resp.status}'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    async def disconnect(self):
        """Disconnect from server"""
        self.should_poll = False
        self.connected = False
        
        if self._poll_task:
            self._poll_task.cancel()
        
        if self.session:
            await self.session.close()
        
        logger.info("Disconnected from HTTP Polling")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected
    
    # API Methods (same as WebSocket)
    async def register_bot(self, main_bot_id: str, token: str, client_secret: str, client_id: str) -> dict:
        return await self.request('register', {
            'mainBotId': main_bot_id,
            'token': token,
            'clientSecret': client_secret,
            'clientId': client_id
        })
    
    async def synchronize(self, bot_id: str, sync_data: dict = None) -> dict:
        return await self.request('synchronization', {
            'botId': bot_id,
            'syncData': sync_data
        })
    
    async def get_gifts(self, bot_id: str) -> dict:
        return await self.request('get_gifts', {'botId': bot_id})
    
    async def create_gift(self, bot_id: str, gift_data: dict) -> dict:
        return await self.request('create_gift', {
            'botId': bot_id,
            'giftData': gift_data
        })
    
    async def delete_gift(self, gift_id: str) -> dict:
        actual_id = gift_id
        if isinstance(gift_id, dict):
            actual_id = gift_id.get('gift_id') or gift_id.get('id')
        return await self.request('delete_gift', {'giftId': str(actual_id)})
    
    async def update_definitions(self, definitions: dict) -> dict:
        return await self.request('update_definitions', {
            'bot_id': self.bot_id,
            'definitions': definitions
        })
    
    async def check_user_verification(self, bot_id: str, user_id: str) -> dict:
        return await self.request('check_user_verification', {
            'botId': bot_id,
            'userId': user_id
        })
    
    async def list_members(self, bot_id: str) -> dict:
        return await self.request('list_members', {'botId': bot_id})
    
    async def check_auth_count(self, bot_id: str) -> dict:
        return await self.request('check_auth_count', {'botId': bot_id})
    
    async def recover_data(self, bot_id: str) -> dict:
        return await self.request('recover', {'botId': bot_id})
