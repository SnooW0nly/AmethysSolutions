"""
WebSocket Manager - Versão Simplificada
Sistema de conexão confiável usando Socket.IO nativo
"""

import asyncio
import json
import socketio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import uuid


class WebSocketManager:
    """Gerenciador de conexão WebSocket simplificado e robusto"""
    
    def __init__(self, server_url: str = None, reconnect_interval: int = 5):
        # Se não foi passada URL, usar do config_api.json
        if server_url is None:
            try:
                from .cloud_config import get_cloud_url
                server_url = get_cloud_url()
            except Exception:
                server_url = "https://cloud.amethys.solutions"
        self.server_url = server_url
        self.reconnect_interval = reconnect_interval
        self.sio: Optional[socketio.AsyncClient] = None
        self.connected = False
        self.connecting = False
        self.should_reconnect = True
        self.logger = logging.getLogger(__name__)
        
        # Callbacks para eventos
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.on_message_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        
        # Sistema de respostas pendentes
        self.pending_responses: Dict[str, asyncio.Future] = {}
        
        # Task de reconexão
        self.reconnect_task: Optional[asyncio.Task] = None
        self.event_processor_task: Optional[asyncio.Task] = None
        
        # Queue para processamento de eventos
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        
        # Informações do bot
        self.bot = None
        self.bot_unique_id: Optional[str] = None
        self.bot_server_id: Optional[str] = None
        self.bot_discord_id: Optional[str] = None
        self.oauth_client_id: Optional[str] = None

    def set_callbacks(self, on_connect: Callable = None, on_disconnect: Callable = None, 
                     on_message: Callable = None, on_error: Callable = None):
        """Define callbacks para eventos do WebSocket"""
        self.on_connect_callback = on_connect
        self.on_disconnect_callback = on_disconnect
        self.on_message_callback = on_message
        self.on_error_callback = on_error
    
    def set_bot(self, bot):
        """Define a instância do bot"""
        from functions.database import database as db
        self.bot = bot
        
        if not bot:
            self.bot_unique_id = None
            self.bot_server_id = None
            self.bot_discord_id = None
            self.oauth_client_id = None
            return
        
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.bot_unique_id = config.get("botID", "SyncBot")
                self.bot_server_id = config.get("bot", {}).get("server")
                
                if hasattr(bot, 'user') and bot.user and hasattr(bot.user, 'id'):
                    self.bot_discord_id = str(bot.user.id)
                else:
                    self.bot_discord_id = config.get("bot", {}).get("id")
                    
                self.logger.info(f"Bot configurado - UniqueID: {self.bot_unique_id}, Server: {self.bot_server_id}")
        except Exception as e:
            self.logger.error(f"Erro ao carregar config.json: {e}")
            self.bot_unique_id = "SyncBot"
            self.bot_server_id = None
            self.bot_discord_id = None
        
        # Carregar oauth_client_id do cloud_data
        cloud_config = db.get_document("cloud_data") or {}
        self.oauth_client_id = cloud_config.get("client_id")
        if self.oauth_client_id:
            self.logger.info(f"OAuth Client ID: {self.oauth_client_id}")

    def get_bot_registration_id(self) -> Optional[str]:
        """Obtém o ID do bot para registro"""
        if hasattr(self, 'bot_discord_id') and self.bot_discord_id:
            return self.bot_discord_id
        if hasattr(self, 'bot') and self.bot and hasattr(self.bot, 'user') and self.bot.user:
            return str(self.bot.user.id)
        return None

    async def start(self):
        """Inicia o gerenciador Socket.IO"""
        if self.reconnect_task and not self.reconnect_task.done():
            self.logger.warning("WebSocket já está iniciado")
            return
        
        self.should_reconnect = True
        
        # Iniciar processador de eventos
        if self.event_processor_task is None or self.event_processor_task.done():
            self.event_processor_task = asyncio.create_task(self._process_event_queue())
        
        # Iniciar loop de reconexão
        self.reconnect_task = asyncio.create_task(self._reconnect_loop())
        self.logger.info("🔄 WebSocket Manager iniciado")

    async def stop(self):
        """Para o gerenciador Socket.IO"""
        self.should_reconnect = False
        
        # Cancelar tasks
        for task in [self.reconnect_task, self.event_processor_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Desconectar
        if self.sio:
            try:
                await self.sio.disconnect()
            except Exception:
                pass
            self.sio = None
        
        self.connected = False
        self.connecting = False
        self.logger.info("🛑 WebSocket Manager parado")

    async def _reconnect_loop(self):
        """Loop de reconexão otimizado"""
        backoff = 2
        max_backoff = 60
        
        while self.should_reconnect:
            try:
                if not self.connected and not self.connecting:
                    # Antes de tentar conectar, garantir que o cliente antigo foi limpo
                    if self.sio:
                        try:
                            await self.sio.disconnect()
                        except:
                            pass
                        self.sio = None

                    await self._connect()
                    
                    if self.connected:
                        backoff = 2  # Reset backoff
                    else:
                        self.logger.info(f"⏳ Próxima tentativa de reconexão em {backoff}s...")
                        await asyncio.sleep(backoff)
                        backoff = min(backoff + 5, max_backoff) # Incremento linear suave
                else:
                    # Verificar saúde da conexão a cada 15 segundos (mais frequente)
                    await asyncio.sleep(15)
                    
                    if self.connected and self.sio:
                        if not self.sio.connected:
                            self.logger.warning("⚠️ Conexão perdida detectada pelo estado do cliente")
                            self.connected = False
                        else:
                            # Teste de latência (ping) para garantir que o socket não está "zumbi"
                            try:
                                await asyncio.wait_for(self.sio.emit('ping_test', {}), timeout=5.0)
                            except Exception:
                                self.logger.warning("⚠️ Servidor não respondeu ao ping, reiniciando conexão...")
                                self.connected = False
                                try:
                                    await self.sio.disconnect()
                                except:
                                    pass
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Erro no loop de reconexão: {e}")
                await asyncio.sleep(5)

    async def _connect(self):
        """Conecta ao servidor Socket.IO"""
        if self.connected or self.connecting:
            return
        
        self.connecting = True
        
        try:
            # Limpar conexão anterior
            if self.sio:
                try:
                    await self.sio.disconnect()
                except Exception:
                    pass
            
            self.logger.info(f"🔄 Conectando ao Socket.IO: {self.server_url}")
            
            # Criar cliente Socket.IO com configurações de estabilidade
            self.sio = socketio.AsyncClient(
                reconnection=True,
                reconnection_attempts=3,
                reconnection_delay=2,
                reconnection_delay_max=10,
                logger=False,
                engineio_logger=False,
                request_timeout=45, # Timeout maior para redes instáveis
            )
            
            # Configurar eventos
            self._setup_events()
            
            # Conectar com timeout
            await asyncio.wait_for(
                self.sio.connect(
                    self.server_url,
                    transports=['websocket', 'polling'],
                    socketio_path='socket.io',
                ),
                timeout=30.0
            )
            
            # Verificar conexão
            await asyncio.sleep(1)
            if hasattr(self.sio, 'connected') and self.sio.connected:
                self.connected = True
                self.logger.info("✅ Conectado ao Socket.IO!")
                
                if self.on_connect_callback:
                    try:
                        await self.on_connect_callback()
                    except Exception as e:
                        self.logger.error(f"Erro no callback de conexão: {e}")
            else:
                raise Exception("Conexão não estabilizou")
                
        except asyncio.TimeoutError:
            self.logger.error("❌ Timeout ao conectar")
        except Exception as e:
            self.logger.error(f"❌ Erro ao conectar: {e}")
            if self.sio:
                try:
                    await self.sio.disconnect()
                except Exception:
                    pass
                self.sio = None
        finally:
            self.connecting = False

    def _setup_events(self):
        """Configura eventos do Socket.IO"""
        if not self.sio:
            return
        
        @self.sio.event
        async def connect():
            self.connected = True
            self.connecting = False
            self.logger.info("✅ Evento connect recebido")
            
            # Atualizar oauth_client_id se necessário
            if not self.oauth_client_id:
                from functions.database import database as db
                cloud_config = db.get_document("cloud_data") or {}
                self.oauth_client_id = cloud_config.get("client_id")
            
            # Enviar informações do bot
            await self._send_bot_connected()
        
        @self.sio.event
        async def disconnect():
            self.logger.info("❌ Desconectado do servidor")
            self.connected = False
            self.connecting = False
            
            if self.on_disconnect_callback:
                try:
                    await self.on_disconnect_callback()
                except Exception as e:
                    self.logger.error(f"Erro no callback de desconexão: {e}")
        
        @self.sio.event
        async def connect_error(data):
            self.logger.error(f"❌ Erro de conexão: {data}")
            self.connected = False
            self.connecting = False
            
            if self.on_error_callback:
                try:
                    await self.on_error_callback(data)
                except Exception:
                    pass
        
        # Eventos de resposta
        self._setup_response_handlers()
        
        # Eventos de ação
        self._setup_action_handlers()

    def _setup_response_handlers(self):
        """Configura handlers de resposta"""
        response_events = [
            'register_response', 'synchronization_response', 'gift_response',
            'update_gift_response', 'delete_gift_response', 'delete_all_gifts_response',
            'get_gifts_response', 'recover_response', 'list_members_response',
            'check_auth_count_response', 'recover_members_response', 
            'check_user_verification_response'
        ]
        
        for event_name in response_events:
            @self.sio.on(event_name)
            async def handler(data, event=event_name):
                self.logger.debug(f"📨 Resposta recebida: {event}")
                if event in self.pending_responses:
                    future = self.pending_responses.pop(event)
                    if not future.done():
                        future.set_result(data)
                
                if self.on_message_callback:
                    await self.on_message_callback({'event': event, 'data': data})

    def _setup_action_handlers(self):
        """Configura handlers de ações do servidor"""
        
        @self.sio.on('redeem_gift')
        async def on_redeem_gift(data):
            if not self._validate_event_ownership(data):
                return
            try:
                self._event_queue.put_nowait({'event': 'redeem_gift', 'data': data})
            except asyncio.QueueFull:
                self.logger.warning("Queue cheia, descartando redeem_gift")
        
        @self.sio.on('recover_members')
        async def on_recover_members(data):
            if not self._validate_event_ownership(data):
                return
            try:
                self._event_queue.put_nowait({'event': 'recover_members', 'data': data})
            except asyncio.QueueFull:
                self.logger.warning("Queue cheia, descartando recover_members")
        
        @self.sio.on('auth_log')
        async def on_auth_log(data):
            self.logger.info(f"📨 auth_log recebido: {data}")
            if not self._validate_event_ownership(data):
                return
            try:
                self._event_queue.put_nowait({'event': 'auth_log', 'data': data})
            except asyncio.QueueFull:
                self.logger.warning("Queue cheia, descartando auth_log")
        
        @self.sio.on('remove_verified_role')
        async def on_remove_verified_role(data):
            if not self._validate_event_ownership(data):
                return
            try:
                self._event_queue.put_nowait({'event': 'remove_verified_role', 'data': data})
            except asyncio.QueueFull:
                self.logger.warning("Queue cheia, descartando remove_verified_role")

    def _validate_event_ownership(self, data: dict) -> bool:
        """Valida se o evento pertence a este bot"""
        try:
            from functions.database import database as db
            
            cloud_config = db.get_document("cloud_data") or {}
            bot_client_id = cloud_config.get("client_id")
            main_server_id = db.obter("config.json").get("bot", {}).get("server")
            
            # Verificar client_id
            event_client_id = data.get("client_id") or data.get("clientId")
            if event_client_id and bot_client_id:
                if str(event_client_id) != str(bot_client_id):
                    return False
            
            # Verificar botId
            event_bot_id = data.get("botId") or data.get("bot_id")
            if event_bot_id and bot_client_id:
                if str(event_bot_id) != str(bot_client_id):
                    return False
            
            # Verificar guild_id
            event_guild_id = data.get("guild_id") or data.get("guildId")
            if event_guild_id and main_server_id:
                if str(event_guild_id) != str(main_server_id):
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao validar ownership: {e}")
            return True  # Em caso de erro, aceitar

    async def _send_bot_connected(self):
        """Envia informações do bot após conectar"""
        if not self.bot:
            return
        
        try:
            # Aguardar bot ficar pronto
            for _ in range(5):
                if hasattr(self.bot, 'user') and self.bot.user:
                    self.bot_discord_id = str(self.bot.user.id)
                    break
                await asyncio.sleep(1)
            
            if not self.bot_discord_id:
                self.logger.error("Bot não está pronto")
                return
            
            # Obter guilds
            guilds = []
            if hasattr(self.bot, 'guilds') and self.bot.guilds:
                guilds = [str(g.id) for g in self.bot.guilds]
            
            registration_data = {
                'bot_id': self.bot_discord_id,
                'unique_id': self.bot_unique_id,
                'server_id': self.bot_server_id,
                'oauth_client_id': self.oauth_client_id,
                'guild_count': len(guilds),
                'guilds': guilds
            }
            
            if self.sio and self.connected:
                await self.sio.emit('bot_connected', registration_data)
                self.logger.info(f"✅ Bot registrado ({len(guilds)} servidores)")
                
                # Sincronizar definições
                if self.oauth_client_id:
                    from functions.database import database as db
                    cloud_config = db.get_document("cloud_data") or {}
                    definitions = cloud_config.get("definitions", {})
                    if definitions:
                        await self.update_definitions(definitions)
                        
        except Exception as e:
            self.logger.error(f"Erro ao enviar bot_connected: {e}")

    async def _process_event_queue(self):
        """Processa eventos da queue"""
        while self.should_reconnect:
            try:
                try:
                    message_data = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                if self.on_message_callback:
                    try:
                        await asyncio.wait_for(
                            self.on_message_callback(message_data),
                            timeout=30.0
                        )
                    except asyncio.TimeoutError:
                        self.logger.error(f"Timeout ao processar: {message_data.get('event')}")
                    except Exception as e:
                        self.logger.error(f"Erro ao processar evento: {e}")
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Erro no processador de eventos: {e}")
                await asyncio.sleep(1)

    async def send_message(self, event: str, data: Dict[str, Any]) -> bool:
        """Envia mensagem via Socket.IO"""
        if not self.connected or not self.sio:
            self.logger.warning("Socket.IO não conectado")
            return False
        
        try:
            if not hasattr(self.sio, 'connected') or not self.sio.connected:
                self.connected = False
                return False
            
            await self.sio.emit(event, data)
            self.logger.debug(f"📤 Mensagem enviada: {event}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar mensagem: {e}")
            self.connected = False
            return False

    async def _wait_for_response(self, request_id: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Aguarda resposta do servidor"""
        try:
            future = asyncio.Future()
            self.pending_responses[request_id] = future
            
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
            
        except asyncio.TimeoutError:
            self.pending_responses.pop(request_id, None)
            return {"success": False, "message": f"Timeout aguardando {request_id}"}
        except Exception as e:
            self.pending_responses.pop(request_id, None)
            return {"success": False, "message": str(e)}

    # ==================== MÉTODOS DE API ====================

    async def register_bot(self, main_bot_id: str, token: str, client_secret: str, client_id: str) -> Dict[str, Any]:
        """Registra um bot"""
        data = {
            "token": token,
            "clientSecret": client_secret,
            "clientId": client_id,
            "mainBotId": main_bot_id
        }
        
        if not await self.send_message("register", data):
            return {"success": False, "message": "Não foi possível enviar mensagem de registro"}
        
        return await self._wait_for_response("register_response", timeout=10.0)

    async def send_synchronization(self, bot_id: str, sync_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia dados de sincronização"""
        data = {"botId": bot_id, "data": sync_data}
        
        if not await self.send_message("synchronization", data):
            return {"success": False, "message": "Não foi possível enviar dados de sincronização"}
        
        return await self._wait_for_response("synchronization_response", timeout=10.0)

    async def send_gift(self, bot_id: str, gift_data: Dict[str, Any]) -> Dict[str, Any]:
        """Envia dados de presente"""
        data = {"botId": bot_id, "giftData": gift_data}
        
        if not await self.send_message("gift", data):
            return {"success": False, "message": "Não foi possível enviar dados de presente"}
        
        return await self._wait_for_response("gift_response", timeout=10.0)

    async def update_gift(self, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza um gift existente"""
        if not await self.send_message("update_gift", update_data):
            return {"success": False, "message": "Não foi possível enviar atualização de gift"}
        
        return await self._wait_for_response("update_gift_response", timeout=10.0)

    async def delete_gift(self, delete_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deleta um gift"""
        if not await self.send_message("delete_gift", delete_data):
            return {"success": False, "message": "Não foi possível enviar deleção de gift"}
        
        return await self._wait_for_response("delete_gift_response", timeout=10.0)

    async def delete_all_gifts(self, delete_data: Dict[str, Any]) -> Dict[str, Any]:
        """Deleta todos os gifts"""
        if not await self.send_message("delete_all_gifts", delete_data):
            return {"success": False, "message": "Não foi possível enviar deleção em massa"}
        
        return await self._wait_for_response("delete_all_gifts_response", timeout=30.0)

    async def get_gifts(self, bot_id: str) -> Dict[str, Any]:
        """Obtém lista de gifts"""
        if not await self.send_message("get_gifts", {"botId": bot_id}):
            return {"success": False, "message": "Não foi possível solicitar gifts"}
        
        return await self._wait_for_response("get_gifts_response", timeout=10.0)

    async def recover_data(self, bot_id: str, recovery_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Recupera dados do servidor"""
        data = {"botId": bot_id, "recoveryData": recovery_data or {}}
        
        if not await self.send_message("recover", data):
            return {"success": False, "message": "Não foi possível solicitar recuperação"}
        
        return await self._wait_for_response("recover_response", timeout=10.0)

    async def list_members(self, bot_id: str) -> Dict[str, Any]:
        """Lista membros do bot"""
        if not await self.send_message("list_members", {"botId": bot_id}):
            return {"success": False, "message": "Não foi possível solicitar lista de membros"}
        
        return await self._wait_for_response("list_members_response", timeout=30.0)

    async def check_auth_count(self, bot_id: str) -> Dict[str, Any]:
        """Verifica contagem de membros autenticados"""
        if not await self.send_message("check_auth_count", {"botId": bot_id}):
            return {"success": False, "message": "Não foi possível solicitar contagem"}
        
        return await self._wait_for_response("check_auth_count_response", timeout=10.0)

    async def recover_members(self, bot_id: str, guild_id: str = None) -> Dict[str, Any]:
        """Recupera membros verificados"""
        data = {"botId": bot_id, "guildId": guild_id}
        
        if not await self.send_message("recover_members", data):
            return {"success": False, "message": "Não foi possível solicitar recuperação de membros"}
        
        return await self._wait_for_response("recover_members_response", timeout=30.0)

    async def update_definitions(self, definitions: dict) -> bool:
        """Envia definições atualizadas para a API"""
        from functions.database import database as db
        
        if not self.connected or not self.sio:
            self.logger.warning("WebSocket não conectado")
            return False
        
        if not self.oauth_client_id:
            cloud_config = db.get_document("cloud_data") or {}
            self.oauth_client_id = cloud_config.get("client_id")
        
        if not self.oauth_client_id:
            self.logger.error("oauth_client_id não configurado")
            return False

        try:
            main_server_id = db.obter("config.json").get("bot", {}).get("server")
        except Exception:
            main_server_id = None

        data = {
            "bot_id": self.oauth_client_id,
            "definitions": definitions,
            "main_server_id": main_server_id
        }
        
        try:
            await self.sio.emit("update_definitions", data)
            self.logger.info("✅ Definições enviadas para a API")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao enviar definições: {e}")
            return False

    async def check_user_verification(self, bot_id: str, user_id: int) -> Dict[str, Any]:
        """Verifica se usuário está verificado"""
        if not self.is_connected():
            return {"success": False, "message": "WebSocket não conectado"}

        data = {"botId": bot_id, "userId": str(user_id)}
        
        if not await self.send_message("check_user_verification", data):
            return {"success": False, "message": "Não foi possível verificar usuário"}
        
        return await self._wait_for_response("check_user_verification_response", timeout=10.0)

    async def resend_bot_connected(self) -> bool:
        """Força reenvio do evento bot_connected"""
        if not self.connected or not self.sio:
            return False
        
        await self._send_bot_connected()
        return True

    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self.connected

    def get_connection_info(self) -> Dict[str, Any]:
        """Retorna informações da conexão"""
        return {
            "connected": self.connected,
            "connecting": self.connecting,
            "server_url": self.server_url,
            "should_reconnect": self.should_reconnect,
            "event_queue_size": self._event_queue.qsize()
        }