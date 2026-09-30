"""
WSManager — WebSocket puro (gorilla/websocket Go server).
Protocolo: {"event": "...", "data": {...}}

Mudança principal vs original:
- Eventos auth_log NÃO criam asyncio.create_task direto.
  São entregues via process_auth_log() que os enfileira de forma controlada.
- Todos os outros eventos ainda criam tasks, mas com proteção de semáforo.
"""
import asyncio
import json
import logging
import traceback
from typing import Dict, Callable, Optional
from datetime import datetime, timedelta
import uuid

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    _USING_UVLOOP = True
except ImportError:
    _USING_UVLOOP = False

import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

logger = logging.getLogger(__name__)

# Semáforo para tasks de eventos não-auth (redeem_gift, recover_members, etc.)
_EVENT_SEMAPHORE: asyncio.Semaphore = None
_MAX_CONCURRENT_EVENTS = 5


def _get_event_semaphore() -> asyncio.Semaphore:
    global _EVENT_SEMAPHORE
    if _EVENT_SEMAPHORE is None:
        _EVENT_SEMAPHORE = asyncio.Semaphore(_MAX_CONCURRENT_EVENTS)
    return _EVENT_SEMAPHORE


class WSManager:
    def __init__(self, bot):
        self.bot               = bot
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected         = False
        self.should_reconnect  = True
        self.reconnect_interval = 3
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = float("inf")

        self.server_url  = None
        self.jwt_secret  = None
        self.bot_id      = None

        self.handlers: Dict[str, Callable] = {}
        self.pending_requests: Dict[str, asyncio.deque] = {}  # event_type -> deque of futures (FIFO)

        logger.info(f"WSManager initialized (uvloop: {_USING_UVLOOP})")

    # ─── Inicialização ────────────────────────────────────────────────────────

    async def initialize(self):
        try:
            config = self._load_config()

            cloud_data = {}
            try:
                from functions.database import database as db
                cloud_data = db.get_document("cloud_data") or {}
            except Exception as e:
                logger.warning(f"cloud_data não encontrado: {e}")

            ws_config = config.get("websocket_cloud", {})

            try:
                from modules.cloud.cloud_config import get_cloud_url
                config_api_url = get_cloud_url()
            except Exception:
                config_api_url = None

            self.server_url = (
                cloud_data.get("server_url")
                or config_api_url
                or ws_config.get("server_url", "https://amethyscloud.stackr.lat")
            )
            self.jwt_secret = ws_config.get("jwt_secret", "sync_secret_key")

            bot_config = config.get("bot", {})
            self.bot_id = cloud_data.get("client_id") or bot_config.get("botID", "AmethysBot")

            self._register_default_handlers()

            client_id     = cloud_data.get("client_id")
            is_configured = bool(client_id and str(client_id).strip())

            if ws_config.get("auto_start", True) and is_configured:
                asyncio.create_task(self.connect())

        except Exception as e:
            logger.error(f"Falha ao inicializar WSManager: {e}")
            traceback.print_exc()

    def _load_config(self) -> dict:
        config = {}
        for path, key in [("configs/config_websocket.json", None), ("config.json", "bot")]:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if key:
                    config[key] = data
                else:
                    config.update(data)
            except Exception as e:
                logger.warning(f"Falha ao carregar {path}: {e}")
        return config

    # ─── JWT ──────────────────────────────────────────────────────────────────

    def _generate_token(self) -> str:
        try:
            import jwt
            discord_id = str(self.bot.user.id) if self.bot and self.bot.user else None
            payload = {
                "botId": str(self.bot_id), "discordId": discord_id,
                "exp": datetime.utcnow() + timedelta(hours=24),
                "iat": datetime.utcnow(),
            }
            return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        except ImportError:
            import base64
            discord_id = str(self.bot.user.id) if self.bot and self.bot.user else None
            return base64.b64encode(
                json.dumps({"botId": str(self.bot_id), "discordId": discord_id}).encode()
            ).decode()

    # ─── Handlers padrão ─────────────────────────────────────────────────────

    def _register_default_handlers(self):
        @self.on("connected")
        async def on_connected(data):
            pass

        @self.on("auth_log")
        async def on_auth_log(data):
            # Delega para a fila controlada — não cria task aqui
            try:
                from modules.cloud.update_api import process_auth_log
                await process_auth_log(data)
            except Exception as e:
                logger.error(f"[WS] Erro ao enfileirar auth_log: {e}")

        @self.on("redeem_gift")
        async def on_redeem_gift(data):
            try:
                from connections.handlers import handle_redeem_gift
                await handle_redeem_gift(self.bot, data)
            except ImportError:
                pass

        @self.on("remove_verified_role")
        async def on_remove_role(data):
            try:
                from connections.handlers import handle_remove_role
                await handle_remove_role(self.bot, data)
            except ImportError:
                pass

    def on(self, event: str):
        def decorator(func):
            self.handlers[event] = func
            return func
        return decorator

    # ─── URL do WebSocket ─────────────────────────────────────────────────────

    def _build_ws_url(self) -> str:
        url = self.server_url
        if url.startswith("http://"):
            url = "ws://" + url[7:]
        elif url.startswith("https://"):
            url = "wss://" + url[8:]
        elif not url.startswith(("ws://", "wss://")):
            url = "wss://" + url
        url = url.rstrip("/")
        if not url.endswith("/ws"):
            url = url + "/ws"
        return url

    # ─── Conexão ──────────────────────────────────────────────────────────────

    async def connect(self):
        while self.should_reconnect:
            try:
                uri = self._build_ws_url()
                logger.info(f"[WS] Conectando a {uri}")
                print(f"🔄 [WSManager] Conectando a {uri}")

                async with websockets.connect(
                    uri,
                    open_timeout=10,
                    # O servidor Go já gerencia keep-alive sozinho:
                    # envia Ping a cada 40s e aguarda Pong em até 90s.
                    # Desabilitamos o ping automático do lado Python para
                    # evitar colisão de frames ping/pong simultâneos, que
                    # confunde o gorilla/websocket e derruba a conexão.
                    ping_interval=None,
                    close_timeout=5,
                    max_size=10_000_000,
                ) as ws:
                    self.ws = ws
                    self.connected = True
                    self.reconnect_attempts = 0
                    self.reconnect_interval = 3  # reset backoff após conexão bem-sucedida

                    print("✅ [WSManager] Conectado!")
                    await self._send_bot_info()
                    await self._listen()

            except ConnectionClosedError as e:
                logger.warning(f"[WS] Conexão fechada: {e}")
            except ConnectionClosedOK:
                logger.info("[WS] Conexão encerrada normalmente")
            except Exception as e:
                logger.debug(f"[WS] Erro de conexão: {type(e).__name__}: {e}")

            self.connected = False
            self.ws = None

            if self.should_reconnect:
                self.reconnect_attempts += 1
                wait = min(self.reconnect_interval * (1.5 ** (self.reconnect_attempts - 1)), 60)
                print(f"🔄 [WSManager] Reconectando em {wait:.1f}s (tentativa {self.reconnect_attempts})")
                await asyncio.sleep(wait)

    # ─── Loop de leitura ──────────────────────────────────────────────────────

    async def _listen(self):
        """
        Processa mensagens recebidas do Go server.
        Eventos auth_log são enfileirados (não criam tasks ilimitadas).
        Demais eventos usam asyncio.create_task com semáforo.
        """
        sem = _get_event_semaphore()
        try:
            async for message in self.ws:
                if not isinstance(message, str):
                    continue
                try:
                    parsed  = json.loads(message)
                    event   = parsed.get("event")
                    payload = parsed.get("data", {})

                    if not event:
                        continue

                    # Respostas a requisições pendentes (fila FIFO por tipo de evento)
                    if event.endswith("_response"):
                        queue = self.pending_requests.get(event)
                        if queue:
                            try:
                                fut = queue.popleft()
                                if not fut.done():
                                    fut.set_result(payload)
                            except IndexError:
                                pass
                            continue

                    if event not in self.handlers:
                        continue

                    handler = self.handlers[event]

                    if event == "auth_log":
                        # auth_log: chamar await diretamente (handler apenas enfileira, é rápido)
                        try:
                            await asyncio.wait_for(handler(payload), timeout=2.0)
                        except asyncio.TimeoutError:
                            logger.warning("[WS] Timeout ao enfileirar auth_log — descartado")
                        except Exception as e:
                            logger.error(f"[WS] Erro ao enfileirar auth_log: {e}")
                    else:
                        # Outros eventos: task com semáforo para limitar concorrência
                        async def _run(h=handler, p=payload):
                            async with sem:
                                try:
                                    await asyncio.wait_for(h(p), timeout=30.0)
                                except asyncio.TimeoutError:
                                    logger.warning(f"[WS] Timeout ao processar evento")
                                except Exception as exc:
                                    logger.error(f"[WS] Erro ao processar evento: {exc}")
                        asyncio.create_task(_run())

                except json.JSONDecodeError:
                    logger.debug("[WS] Mensagem inválida (não-JSON)")
                except Exception as e:
                    logger.debug(f"[WS] Erro ao processar mensagem: {e}")
        except Exception as e:
            logger.debug(f"[WS] Loop de leitura encerrado: {e}")

    # ─── Envio ────────────────────────────────────────────────────────────────

    async def send(self, event: str, data: dict, request_id: str = None) -> bool:
        if not self.ws or not self.connected:
            return False
        try:
            if request_id:
                data = dict(data)
                data["requestId"] = request_id
            await self.ws.send(json.dumps({"event": event, "data": data}))
            return True
        except Exception as e:
            logger.error(f"[WS] Falha ao enviar '{event}': {e}")
            self.connected = False
            return False

    async def request(self, event: str, data: dict, timeout: float = 30.0) -> dict:
        if not self.ws or not self.connected:
            return {"success": False, "message": "Not connected"}

        response_event = event + "_response"

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        future = loop.create_future()

        # Fila FIFO por tipo de evento: o servidor Go responde na mesma ordem
        # que recebe, sem requestId. Múltiplas requisições do mesmo tipo são
        # resolvidas em ordem de chegada.
        if response_event not in self.pending_requests:
            from collections import deque
            self.pending_requests[response_event] = deque()
        self.pending_requests[response_event].append(future)

        try:
            ok = await self.send(event, data)
            if not ok:
                try:
                    self.pending_requests[response_event].remove(future)
                except Exception:
                    pass
                return {"success": False, "message": "Failed to send"}
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            try:
                self.pending_requests[response_event].remove(future)
            except Exception:
                pass
            return {"success": False, "message": "Request timeout"}
        except Exception as e:
            try:
                self.pending_requests[response_event].remove(future)
            except Exception:
                pass
            return {"success": False, "message": str(e)}

    # ─── Info do bot ──────────────────────────────────────────────────────────

    async def _send_bot_info(self):
        try:
            config     = self._load_config()
            bot_config = config.get("bot", {})
            guilds     = [str(g.id) for g in self.bot.guilds] if self.bot and self.bot.guilds else []

            # Fetch oauth_client_id — non-blocking, DB read is fast but do it once
            oauth_client_id = None
            discord_bot_id  = str(self.bot.user.id) if self.bot and self.bot.user else None
            try:
                from functions.database import database as db
                cloud_cfg       = db.get_document("cloud_data") or {}
                oauth_client_id = cloud_cfg.get("client_id")
            except Exception:
                pass

            data = {
                "bot_id":         oauth_client_id or discord_bot_id,
                "oauth_client_id": oauth_client_id,
                "unique_id":      bot_config.get("botID"),
                "server_id":      bot_config.get("bot", {}).get("server"),
                "discord_bot_id": discord_bot_id,
                "guilds":         guilds,
            }

            ok = await self.send("bot_connected", data)
            if ok:
                print(f"📤 [WSManager] Registrado como bot_id={data['bot_id']} ({len(guilds)} guilds)")
        except Exception as e:
            logger.error(f"[WS] Falha ao enviar bot_info: {e}")

    # ─── Lifecycle ────────────────────────────────────────────────────────────

    async def disconnect(self):
        self.should_reconnect = False
        if self.ws:
            await self.ws.close()
        self.connected = False
        self.ws = None

    def is_connected(self) -> bool:
        return self.connected and self.ws is not None

    # ─── API Methods ──────────────────────────────────────────────────────────

    async def register_bot(self, main_bot_id, token, client_secret, client_id):
        return await self.request("register", {
            "mainBotId": main_bot_id, "token": token,
            "clientSecret": client_secret, "clientId": client_id,
        })

    async def synchronize(self, bot_id, sync_data=None):
        return await self.request("synchronization", {"botId": bot_id, "syncData": sync_data})

    async def get_gifts(self, bot_id):
        return await self.request("get_gifts", {"botId": bot_id})

    async def create_gift(self, bot_id, gift_data):
        return await self.request("gift", {"botId": bot_id, "giftData": gift_data})

    async def delete_gift(self, gift_id):
        actual = gift_id.get("gift_id") or gift_id.get("id") if isinstance(gift_id, dict) else gift_id
        return await self.request("delete_gift", {"gift_id": str(actual), "giftId": str(actual)})

    async def delete_all_gifts(self, delete_data):
        return await self.request("delete_all_gifts", delete_data)

    async def update_gift(self, update_data):
        return await self.request("update_gift", update_data)

    async def update_definitions(self, definitions):
        config     = self._load_config()
        bot_config = config.get("bot", {})
        cloud_cfg  = {}
        try:
            from functions.database import database as db
            cloud_cfg = db.get_document("cloud_data") or {}
        except Exception:
            pass
        return await self.request("update_definitions", {
            "bot_id":        cloud_cfg.get("client_id"),
            "definitions":   definitions,
            "main_server_id": bot_config.get("bot", {}).get("server"),
        })

    async def check_user_verification(self, bot_id, user_id):
        return await self.request("check_user_verification",
                                  {"botId": bot_id, "userId": str(user_id)})

    async def list_members(self, bot_id):
        return await self.request("list_members", {"botId": bot_id})

    async def check_auth_count(self, bot_id):
        return await self.request("check_auth_count", {"botId": bot_id})

    async def recover_data(self, bot_id):
        return await self.request("recover", {"botId": bot_id})

    # ─── Compatibilidade retroativa ───────────────────────────────────────────

    def set_bot(self, bot):
        self.bot = bot

    async def start(self):
        await self.initialize()

    async def stop(self):
        await self.disconnect()

    def set_callbacks(self, on_connect=None, on_disconnect=None,
                      on_error=None, on_message=None):
        if on_message:
            self._legacy_on_message = on_message

    async def resend_bot_connected(self):
        await self._send_bot_info()