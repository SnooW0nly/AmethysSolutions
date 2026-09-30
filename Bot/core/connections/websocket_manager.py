import asyncio
import json
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import socketio
import aiohttp

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manager for WebSocket connection to Sync API Manager"""
    
    def __init__(self, bot):
        self.bot = bot
        self.sio = None
        self.session = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = float('inf')  # Infinite reconnection attempts
        self.reconnect_interval = 5
        self.reconnect_task = None
        self.should_reconnect = True
        self.handlers = {}
        self.pending_requests = {}
        self.config = None
        self.server_url = None
        
    async def initialize(self):
        """Initialize WebSocket connection"""
        try:
            # Load configuration
            self.config = self._load_config()
            self.server_url = self.config.get('websocket_manager', {}).get('server_url', 'https://manager.syncapplications.com.br')
            
            # Create session and socket.io client
            self.session = aiohttp.ClientSession()
            self.sio = socketio.AsyncClient(
                reconnection=False,  # We'll handle reconnection manually
                logger=False,
                engineio_logger=False
            )
            
            # Register event handlers
            self._register_handlers()
            
            # Register function handlers
            self._register_function_handlers()
            
            # Start connection if auto_start is enabled
            if self.config.get('websocket_manager', {}).get('auto_start', True):
                await self.connect()
                
            logger.info("WebSocket Manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize WebSocket Manager: {e}")
            logger.error(traceback.format_exc())
    
    def _load_config(self) -> dict:
        """Load configuration from files"""
        config = {}
        
        # Load websocket config
        try:
            with open('configs/config_websocket.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load websocket config: {e}")
        
        # Load main config
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                main_config = json.load(f)
                config['bot'] = main_config
        except Exception as e:
            logger.error(f"Failed to load main config: {e}")
        
        return config
    
    def _register_handlers(self):
        """Register Socket.IO event handlers"""
        
        @self.sio.event
        async def connect():
            """Handle connection event"""
            self.connected = True
            self.reconnect_attempts = 0
            logger.info("Connected to WebSocket Manager")
            
            # Send authentication
            await self._authenticate()
        
        @self.sio.event
        async def disconnect():
            """Handle disconnection event"""
            self.connected = False
            logger.warning("Disconnected from WebSocket Manager")
            
            # Start automatic reconnection
            if self.should_reconnect:
                logger.info("Starting automatic reconnection...")
                asyncio.create_task(self._auto_reconnect())
        
        @self.sio.event
        async def auth_success(data):
            """Handle successful authentication"""
            logger.info(f"Authentication successful: {data.get('message')}")
            
            # Send initial status
            await self._send_status()
        
        @self.sio.event
        async def auth_error(data):
            """Handle authentication error"""
            logger.error(f"Authentication failed: {data.get('message')}")
            self.connected = False
        
        @self.sio.event
        async def auth_kicked(data):
            """Handle being kicked due to new connection"""
            logger.warning(f"Kicked from server: {data.get('message')}")
            self.connected = False
        
        @self.sio.event
        async def execute(data):
            """Handle function execution request"""
            await self._handle_execute(data)
        
        @self.sio.event
        async def heartbeat(data):
            """Handle heartbeat from server"""
            await self.sio.emit('heartbeat_ack', {
                'timestamp': data.get('timestamp'),
                'received': datetime.now().isoformat()
            })
        
        @self.sio.event
        async def pong(data):
            """Handle pong response"""
            logger.debug(f"Pong received: {data}")
    
    async def _authenticate(self):
        """Send authentication to server"""
        try:
            bot_config = self.config.get('bot', {})
            guild = self.bot.get_guild(int(bot_config.get('bot', {}).get('server')))
            
            auth_data = {
                'botId': bot_config.get('botID'),
                'botToken': bot_config.get('botToken'),
                'discordId': str(self.bot.user.id) if self.bot.user else None,
                'serverInfo': {
                    'id': str(guild.id) if guild else None,
                    'name': guild.name if guild else None
                } if guild else None
            }
            
            await self.sio.emit('bot:auth', auth_data)
            logger.info(f"Authentication sent for bot {auth_data['botId']}")
            
        except Exception as e:
            logger.error(f"Failed to authenticate: {e}")
            logger.error(traceback.format_exc())
    
    async def _send_status(self):
        """Send bot status to server"""
        try:
            status_data = {
                'status': 'online',
                'uptime': self.bot.uptime.total_seconds() if hasattr(self.bot, 'uptime') else 0,
                'version': self.config.get('bot', {}).get('version', '1.0.0'),
                'guilds': len(self.bot.guilds),
                'users': len(self.bot.users),
                'commands': len(self.bot.slash_commands)
            }
            
            await self.sio.emit('bot:status', status_data)
            
        except Exception as e:
            logger.error(f"Failed to send status: {e}")
    
    async def _handle_execute(self, data):
        """Handle function execution request"""
        request_id = data.get('requestId')
        function_type = data.get('type')
        payload = data.get('payload', {})
        
        try:
            # Check if handler exists
            if function_type not in self.handlers:
                await self._send_response(request_id, {
                    'error': f'Function {function_type} not implemented',
                    'status': 'error'
                })
                return
            
            # Execute handler
            handler = self.handlers[function_type]
            result = await handler(self.bot, payload)
            
            # Send response
            await self._send_response(request_id, {
                'data': result,
                'status': 'success'
            })
            
        except Exception as e:
            logger.error(f"Error executing function {function_type}: {e}")
            logger.error(traceback.format_exc())
            
            await self._send_response(request_id, {
                'error': str(e),
                'status': 'error'
            })
    
    async def _send_response(self, request_id: str, response: dict):
        """Send response back to server"""
        try:
            await self.sio.emit('bot:response', {
                'requestId': request_id,
                **response
            })
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
    
    def _register_function_handlers(self):
        """Register all function handlers"""
        from .handlers import register_all_handlers
        self.handlers = register_all_handlers()
        logger.info(f"Registered {len(self.handlers)} function handlers")
    
    async def _auto_reconnect(self):
        """Automatically reconnect with exponential backoff"""
        if self.reconnect_task and not self.reconnect_task.done():
            return  # Already reconnecting
        
        self.reconnect_attempts = 0
        base_interval = self.reconnect_interval
        max_interval = 60  # Max 60 seconds between attempts
        
        while self.should_reconnect and not self.connected:
            self.reconnect_attempts += 1
            
            # Calculate backoff with exponential increase (capped at max_interval)
            wait_time = min(base_interval * (1.5 ** (self.reconnect_attempts - 1)), max_interval)
            
            logger.info(f"Reconnection attempt {self.reconnect_attempts} in {wait_time:.1f} seconds...")
            await asyncio.sleep(wait_time)
            
            if not self.should_reconnect:
                break
            
            try:
                logger.info(f"Attempting to reconnect to {self.server_url}")
                await self.sio.connect(
                    self.server_url,
                    transports=['websocket', 'polling']
                )
                
                if self.connected:
                    logger.info(f"✅ Reconnected successfully after {self.reconnect_attempts} attempts")
                    self.reconnect_attempts = 0
                    break
                    
            except Exception as e:
                logger.debug(f"Reconnection attempt {self.reconnect_attempts} failed: {e}")
                continue
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            if self.connected:
                logger.warning("Already connected to WebSocket Manager")
                return
            
            logger.info(f"Connecting to WebSocket Manager at {self.server_url}")
            await self.sio.connect(
                self.server_url,
                transports=['websocket', 'polling']
            )
            
        except Exception as e:
            logger.debug(f"Failed to connect to WebSocket Manager: {e}")
            
            # Start automatic reconnection
            if self.should_reconnect:
                asyncio.create_task(self._auto_reconnect())
    
    async def disconnect(self, stop_reconnect=True):
        """Disconnect from WebSocket server
        
        Args:
            stop_reconnect: If True, stops automatic reconnection attempts
        """
        try:
            # Stop reconnection if requested
            if stop_reconnect:
                self.should_reconnect = False
            
            if self.sio:
                await self.sio.disconnect()
            
            if self.session:
                await self.session.close()
            
            self.connected = False
            logger.info("Disconnected from WebSocket Manager")
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
    
    async def emit_event(self, event_type: str, data: dict):
        """Emit event to server"""
        try:
            if not self.connected:
                logger.warning(f"Cannot emit event {event_type}: not connected")
                return
            
            await self.sio.emit('bot:event', {
                'type': event_type,
                'data': data,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to emit event {event_type}: {e}")
    
    async def send_log(self, level: str, message: str, meta: dict = None):
        """Send log to server"""
        try:
            if not self.connected:
                return
            
            await self.sio.emit('bot:log', {
                'level': level,
                'message': message,
                'meta': meta or {},
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to send log: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to server"""
        return self.connected
