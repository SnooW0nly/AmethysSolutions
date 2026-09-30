"""
Cliente WebSocket para API de Pagamentos
Recebe notificações em tempo real de pagamentos aprovados
"""
import asyncio
import logging
from typing import Optional, Callable, Dict, Any
import socketio
from functions.database import database as db

logger = logging.getLogger(__name__)


class PaymentWebSocketClient:
    """Cliente WebSocket para notificações de pagamento"""
    
    def __init__(self, bot):
        self.bot = bot
        self.server_url = self._get_api_url()
        self.sio = socketio.AsyncClient(
            reconnection=True,
            reconnection_attempts=0,  # Infinito
            reconnection_delay=2,
            reconnection_delay_max=30,
            logger=False,
            engineio_logger=False
        )
        self.connected = False
        self.bot_id = None
        self.bot_token = None
        
        # Callback para pagamento aprovado
        self.on_payment_approved: Optional[Callable] = None
        
        self._setup_events()
    
    def _get_api_url(self) -> str:
        """Obtém URL da API do config"""
        try:
            config = db.obter("configs/config_api.json") or {}
            api_url = config.get("payments", "localhost:22222")
            
            # Adicionar http:// se não tiver
            if not api_url.startswith("http"):
                api_url = f"http://{api_url}"
            
            return api_url
        except Exception:
            return "https://amethyspayments.stackr.lat"
    
    def _setup_events(self):
        """Configurar eventos do Socket.IO"""
        
        @self.sio.event
        async def connect():
            """Conectado ao servidor"""
            self.connected = True
            logger.info(f"✅ Conectado à API de Pagamentos: {self.server_url}")
            
            # Autenticar automaticamente
            if self.bot_id and self.bot_token:
                await self.authenticate(self.bot_id, self.bot_token)
        
        @self.sio.event
        async def disconnect():
            """Desconectado do servidor"""
            self.connected = False
            logger.warning("⚠️ Desconectado da API de Pagamentos")
        
        @self.sio.event
        async def connected(data):
            """Confirmação de conexão"""
            logger.info(f"Servidor: {data.get('message')}")
        
        @self.sio.event
        async def auth_success(data):
            """Autenticação bem-sucedida"""
            logger.info(f"✅ Autenticado na API de Pagamentos")
            logger.info(f"Bot ID: {data.get('botId')}")
        
        @self.sio.event
        async def auth_error(data):
            """Erro na autenticação"""
            logger.error(f"❌ Erro de autenticação: {data.get('message')}")
        
        @self.sio.on('payment:update')
        async def on_payment_update(data):
            """Atualização de pagamento"""
            payment_id = data.get('payment_id')
            status = data.get('status')
            
            logger.info(f"🔄 Pagamento atualizado: {payment_id} - Status: {status}")
            
            # Se foi aprovado, chamar callback
            if status == 'approved' and self.on_payment_approved:
                try:
                    await self.on_payment_approved(data)
                except Exception as e:
                    logger.error(f"Erro no callback payment_approved: {e}")
        
        @self.sio.event
        async def watching_payment(data):
            """Confirmação de monitoramento"""
            logger.info(f"👁️ Monitorando pagamento: {data.get('paymentId')}")
        
        @self.sio.event
        async def error(data):
            """Erro genérico"""
            logger.error(f"❌ Erro: {data.get('message')}")
    
    async def connect(self):
        """Conectar ao servidor"""
        try:
            if self.connected:
                logger.warning("Já conectado à API de Pagamentos")
                return
            
            logger.info(f"Conectando à API de Pagamentos: {self.server_url}")
            await self.sio.connect(self.server_url, transports=['websocket', 'polling'])
            
        except Exception as e:
            logger.error(f"Erro ao conectar: {e}")
            # Não lançar exceção, deixar reconexão automática tentar
    
    async def disconnect(self):
        """Desconectar do servidor"""
        try:
            if self.sio.connected:
                await self.sio.disconnect()
            self.connected = False
            logger.info("Desconectado da API de Pagamentos")
        except Exception as e:
            logger.error(f"Erro ao desconectar: {e}")
    
    async def authenticate(self, bot_id: str, bot_token: str):
        """Autenticar bot"""
        try:
            self.bot_id = bot_id
            self.bot_token = bot_token
            
            await self.sio.emit('bot:auth', {
                'botId': bot_id,
                'botToken': bot_token
            })
            
        except Exception as e:
            logger.error(f"Erro ao autenticar: {e}")
    
    async def watch_payment(self, payment_id: str):
        """Monitorar um pagamento específico"""
        try:
            if not self.connected:
                logger.warning("Não conectado à API de Pagamentos")
                return
            
            await self.sio.emit('watch:payment', {
                'paymentId': payment_id
            })
            
        except Exception as e:
            logger.error(f"Erro ao monitorar pagamento: {e}")
    
    async def unwatch_payment(self, payment_id: str):
        """Parar de monitorar um pagamento"""
        try:
            if not self.connected:
                return
            
            await self.sio.emit('unwatch:payment', {
                'paymentId': payment_id
            })
            
        except Exception as e:
            logger.error(f"Erro ao parar de monitorar: {e}")
    
    def set_payment_approved_callback(self, callback: Callable):
        """Define callback para quando pagamento for aprovado"""
        self.on_payment_approved = callback
    
    def is_connected(self) -> bool:
        """Verificar se está conectado"""
        return self.connected


# Instância global
_ws_client: Optional[PaymentWebSocketClient] = None


def get_ws_client() -> Optional[PaymentWebSocketClient]:
    """Obter instância global do cliente"""
    return _ws_client


def initialize_ws_client(bot) -> PaymentWebSocketClient:
    """Inicializar cliente WebSocket"""
    global _ws_client
    _ws_client = PaymentWebSocketClient(bot)
    return _ws_client


async def start_ws_client(bot_id: str, bot_token: str):
    """Iniciar e conectar cliente WebSocket"""
    if _ws_client is None:
        raise RuntimeError("Cliente WebSocket não inicializado. Use initialize_ws_client() primeiro.")
    
    await _ws_client.connect()
    await _ws_client.authenticate(bot_id, bot_token)


async def stop_ws_client():
    """Parar cliente WebSocket"""
    if _ws_client:
        await _ws_client.disconnect()
