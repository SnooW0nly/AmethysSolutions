"""
ExtensionsWebSocketManager — Socket.IO v4 client via websockets puro.

Remove a dependência de python-socketio / aiohttp (que quebrou com ClientWSTimeout).
Implementa o protocolo Engine.IO v4 + Socket.IO v4 diretamente sobre websockets,
espelhando a arquitetura do WSManager (connect loop, _listen, reconnect backoff).

Protocolo resumido:
  EIO tipos: 0=open 1=close 2=ping 3=pong 4=message 5=upgrade 6=noop
  SIO tipos (dentro do EIO-4): 0=connect 1=disconnect 2=event 3=ack 4=error

  Handshake:
    WS connect → server envia "0{...json...}"
    Client envia "40"  (SIO connect namespace /)
    Server envia "40{...}" (confirmado)

  Emit:   client envia  '42["event", data]'
  Receive: server envia '42["event", data]'
  Ping:   server envia '2', client responde '3'
"""

import asyncio
import json
import logging
import hashlib
from typing import Dict, Any, Optional, Callable

import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

logger = logging.getLogger(__name__)

_RESPONSE_EVENTS = [
    'create_gift_response',
    'get_gifts_response',
    'update_gift_response',
    'delete_gift_response',
    'delete_all_gifts_response',
    'add_account_token_response',
    'get_account_tokens_response',
    'delete_account_token_response',
    'get_oauth_cache_response',
    'run_boost_response',
]

# ─── Engine.IO / Socket.IO helpers ────────────────────────────────────────────

def _sio_emit_packet(event: str, data: Any) -> str:
    """Formata um pacote Socket.IO event: '42["event", data]'"""
    return "42" + json.dumps([event, data], ensure_ascii=False)


def _parse_sio_packet(raw: str):
    """
    Retorna (eio_type, sio_type, payload) ou None se inválido.
    eio_type: int (0-6)
    sio_type: int ou None (se não for EIO message=4)
    payload:  dict/list/str ou None
    """
    if not raw:
        return None

    try:
        eio_type = int(raw[0])
    except (ValueError, IndexError):
        return None

    if eio_type != 4:                      # não é EIO message — ping, pong, open…
        return eio_type, None, raw[1:]

    if len(raw) < 2:
        return eio_type, None, None

    try:
        sio_type = int(raw[1])
    except ValueError:
        return eio_type, None, raw[1:]

    body = raw[2:]

    payload = None
    if body:
        try:
            payload = json.loads(body)
        except Exception:
            payload = body

    return eio_type, sio_type, payload


# ─── Manager ──────────────────────────────────────────────────────────────────

class ExtensionsWebSocketManager:

    def __init__(self, bot):
        self.bot = bot

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected   = False
        self.connecting  = False
        self.should_reconnect = True

        self.server_url        = None
        self.reconnect_interval = 5
        self.api_key: Optional[str] = None

        self.pending_responses: Dict[str, asyncio.Future] = {}
        self.handlers:          Dict[str, Callable]       = {}

        self._reconnect_attempt = 0
        self._connect_task: Optional[asyncio.Task] = None

    # ─── Config & key ─────────────────────────────────────────────────────────

    def _generate_api_key(self, bot_id: str) -> str:
        salt = "sync_boost_api_2024"
        return hashlib.sha256(f"{bot_id}_{salt}".encode()).hexdigest()

    def _load_config(self):
        try:
            with open('configs/config_websocket.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            boost_config       = config.get('websocket_boost', {})
            self.server_url    = boost_config.get('server_url', 'https://amethysboost.stackr.lat')
            self.reconnect_interval = boost_config.get('reconnect_interval', 5)
        except Exception as e:
            logger.error(f"[ExtensionsWS] Erro ao carregar config: {e}")
            self.server_url = 'https://amethysboost.stackr.lat'

    def _build_ws_url(self) -> str:
        """Converte URL HTTP(S) → WSS e adiciona path Engine.IO."""
        url = self.server_url or ''
        if url.startswith('https://'):
            url = 'wss://' + url[8:]
        elif url.startswith('http://'):
            url = 'ws://' + url[7:]
        elif not url.startswith(('ws://', 'wss://')):
            url = 'wss://' + url
        url = url.rstrip('/')
        # Engine.IO v4 endpoint
        return url + '/socket.io/?EIO=4&transport=websocket'

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def initialize(self):
        self._load_config()

        if self.bot and getattr(self.bot, 'user', None):
            self.api_key = self._generate_api_key(str(self.bot.user.id))

        self.should_reconnect   = True
        self._reconnect_attempt = 0

        self._connect_task = asyncio.create_task(self._connect_loop())

    async def _connect_loop(self):
        """Loop de conexão com backoff exponencial — igual ao WSManager."""
        while self.should_reconnect:
            if self.connecting or self.connected:
                await asyncio.sleep(1)
                continue

            self.connecting = True
            try:
                uri = self._build_ws_url()
                logger.info(f"[ExtensionsWS] Conectando a {uri}")

                async with websockets.connect(
                    uri,
                    ping_interval=None,   # heartbeat gerenciado pelo Engine.IO
                    ping_timeout=None,
                    close_timeout=10,
                    max_size=10_000_000,
                    open_timeout=15,
                ) as ws:
                    self.ws         = ws
                    self.connecting = False

                    # ── Handshake Engine.IO ──────────────────────────
                    try:
                        open_msg = await asyncio.wait_for(ws.recv(), timeout=10)
                        parsed   = _parse_sio_packet(open_msg)
                        if not parsed or parsed[0] != 0:
                            logger.warning(f"[ExtensionsWS] Handshake inesperado: {open_msg!r}")
                    except asyncio.TimeoutError:
                        logger.warning("[ExtensionsWS] Timeout no handshake EIO open")

                    # ── SIO connect namespace / ──────────────────────
                    await ws.send("40")

                    # ── Aguarda confirmação SIO connect ─────────────
                    try:
                        confirm = await asyncio.wait_for(ws.recv(), timeout=10)
                        parsed  = _parse_sio_packet(confirm)
                        # EIO=4, SIO=0 → namespace conectado
                        if parsed and parsed[0] == 4 and parsed[1] == 0:
                            self.connected          = True
                            self._reconnect_attempt = 0
                            logger.info(f"[ExtensionsWS] ✅ Conectado: {self.server_url}")
                            await self._send_bot_info()
                    except asyncio.TimeoutError:
                        # Alguns servidores não enviam confirmação explícita — tudo bem
                        self.connected          = True
                        self._reconnect_attempt = 0
                        logger.info(f"[ExtensionsWS] ✅ Conectado (sem confirm): {self.server_url}")
                        await self._send_bot_info()

                    await self._listen(ws)

            except ConnectionClosedOK:
                logger.info("[ExtensionsWS] 🔌 Conexão encerrada normalmente")
            except ConnectionClosedError as e:
                logger.warning(f"[ExtensionsWS] 🔌 Conexão fechada: {e}")
            except Exception as e:
                logger.error(f"[ExtensionsWS] ❌ Falha ao conectar: {type(e).__name__}: {e}")
            finally:
                self.connected  = False
                self.connecting = False
                self.ws         = None

                # Cancela futures pendentes
                for fut in list(self.pending_responses.values()):
                    if not fut.done():
                        fut.cancel()
                self.pending_responses.clear()

            if self.should_reconnect:
                self._reconnect_attempt += 1
                wait = min(
                    self.reconnect_interval * (1.5 ** (self._reconnect_attempt - 1)),
                    60,
                )
                logger.info(f"[ExtensionsWS] Reconectando em {wait:.1f}s (tentativa {self._reconnect_attempt})")
                await asyncio.sleep(wait)

    # ─── Loop de leitura ──────────────────────────────────────────────────────

    async def _listen(self, ws):
        """Processa mensagens Socket.IO recebidas."""
        async for raw in ws:
            if not isinstance(raw, str):
                continue

            parsed = _parse_sio_packet(raw)
            if parsed is None:
                continue

            eio_type, sio_type, payload = parsed

            # Engine.IO ping → responde pong
            if eio_type == 2:
                try:
                    await ws.send('3')
                except Exception:
                    pass
                continue

            # EIO close
            if eio_type == 1:
                logger.info("[ExtensionsWS] Servidor enviou EIO close")
                break

            # Só nos importa EIO message (4) + SIO event (2)
            if eio_type != 4 or sio_type != 2:
                continue

            # payload deve ser [event_name, data]
            if not isinstance(payload, list) or len(payload) < 1:
                continue

            event_name = payload[0]
            data       = payload[1] if len(payload) > 1 else {}

            # ── Resolve futures de request() ──────────────────────
            future = self.pending_responses.pop(event_name, None)
            if future and not future.done():
                future.set_result(data)
                continue

            # ── Handlers registrados pelo usuário ─────────────────
            handler = self.handlers.get(event_name)
            if handler:
                try:
                    await asyncio.wait_for(handler(data), timeout=30.0)
                except asyncio.TimeoutError:
                    logger.warning(f"[ExtensionsWS] Timeout ao processar '{event_name}'")
                except Exception as e:
                    logger.error(f"[ExtensionsWS] Erro no handler '{event_name}': {e}")

    # ─── Emissão ──────────────────────────────────────────────────────────────

    async def emit(self, event: str, data: Any) -> bool:
        if not self.ws or not self.connected:
            return False
        try:
            await self.ws.send(_sio_emit_packet(event, data))
            return True
        except Exception as e:
            logger.error(f"[ExtensionsWS] Erro ao emitir '{event}': {e}")
            self.connected = False
            return False

    async def request(self, event: str, data: dict, timeout: float = 30.0):
        if not self.connected or not self.ws:
            return {'success': False, 'message': 'Não conectado'}

        response_event = f"{event}_response"

        loop   = asyncio.get_running_loop()
        future = loop.create_future()
        self.pending_responses[response_event] = future

        try:
            ok = await self.emit(event, data)
            if not ok:
                self.pending_responses.pop(response_event, None)
                return {'success': False, 'message': 'Falha ao enviar'}

            return await asyncio.wait_for(future, timeout)

        except asyncio.TimeoutError:
            self.pending_responses.pop(response_event, None)
            return {'success': False, 'message': 'Timeout'}

        except Exception as e:
            self.pending_responses.pop(response_event, None)
            return {'success': False, 'message': str(e)}

    # ─── Bot info ─────────────────────────────────────────────────────────────

    async def _send_bot_info(self):
        if not self.bot or not self.api_key:
            return
        try:
            payload = {
                'bot_id':   str(self.bot.user.id),
                'unique_id': "SyncBot",
                'api_key':  self.api_key,
                'site_mode': True,
            }
            await self.emit('bot_connected', payload)
        except Exception as e:
            logger.error(f"[ExtensionsWS] Erro bot_info: {e}")

    # ─── Stop ─────────────────────────────────────────────────────────────────

    async def stop(self):
        self.should_reconnect = False

        if self._connect_task:
            self._connect_task.cancel()

        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass

        self.connected = False

    # ─── API pública ──────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self.connected and self.ws is not None

    def on(self, event: str):
        """Decorator para registrar handlers de eventos."""
        def decorator(func):
            self.handlers[event] = func
            return func
        return decorator

    # ─── Compatibilidade com código existente ─────────────────────────────────

    async def connect(self):
        """Compat: inicia o loop de conexão se ainda não estiver rodando."""
        if not self._connect_task or self._connect_task.done():
            self._connect_task = asyncio.create_task(self._connect_loop())


# ─── Singleton ────────────────────────────────────────────────────────────────

_extensions_ws_manager: Optional[ExtensionsWebSocketManager] = None


def get_extensions_ws(bot=None) -> ExtensionsWebSocketManager:
    global _extensions_ws_manager

    if _extensions_ws_manager is None:
        if bot is None:
            raise ValueError("Bot instance is required for the first initialization")
        _extensions_ws_manager = ExtensionsWebSocketManager(bot)

    return _extensions_ws_manager
