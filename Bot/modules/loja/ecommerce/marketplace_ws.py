"""
marketplace_ws.py
=================
Cliente WebSocket para o servidor Marketplace (Ruby/Faye).

O servidor Ruby implementa Engine.IO manualmente via faye-websocket.
Usamos websockets puro em vez de python-socketio para ter controle
total do handshake Engine.IO/Socket.IO.

Protocolo:
  Engine.IO:
    "0{json}"  → open   (servidor envia ao conectar)
    "2"        → ping   (cliente envia a cada ~25s)
    "3"        → pong   (servidor responde ao ping)
    "4{sio}"   → message (carrega payload Socket.IO)

  Socket.IO (dentro do "4"):
    "40{json}" → CONNECT  (cliente envia auth, servidor confirma com "40")
    "42{json}" → EVENT    [event_name, data]
    "44{json}" → CONNECT_ERROR
"""

import asyncio
import json
import logging
import traceback
from typing import Optional, Callable, Dict

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)


def _get_api_url() -> str:
    try:
        with open("configs/config_api.json", "r", encoding="utf-8") as f:
            url = json.load(f).get("marketplace", "https://amethysmarcktplace.stackr.lat")
        url = url.rstrip("/")
        if url.startswith("https://"):
            return "wss://" + url[8:]
        if url.startswith("http://"):
            return "ws://" + url[7:]
        return url
    except Exception:
        return "wss://amethysmarcktplace.stackr.lat"


def _get_api_secret() -> str:
    try:
        with open("configs/config_api.json", "r", encoding="utf-8") as f:
            return json.load(f).get("marketplace_secret", "")
    except Exception:
        return ""


class MarketplaceWSClient:
    def __init__(self, bot):
        self.bot = bot
        self._bot_id: Optional[str] = None
        self._handlers: Dict[str, Callable] = {}
        self._ws = None
        self._connected = False
        self._running = False
        self._ping_task: Optional[asyncio.Task] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._connected and self._ws is not None

    async def start(self):
        self._running = True
        await asyncio.sleep(2)
        asyncio.create_task(self._connect_loop())

    async def stop(self):
        self._running = False
        self._connected = False
        if self._ping_task:
            self._ping_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass

    def on(self, event: str):
        def decorator(func):
            self._handlers[event] = func
            return func
        return decorator

    async def emit_cart_update(self, cart_id: str, cart: dict):
        await self._emit("cart_update", {"bot_id": self._bot_id, "cart_id": cart_id, "cart": cart})

    async def emit_payment_created(self, cart_id: str, payment: dict):
        await self._emit("payment_created", {"bot_id": self._bot_id, "cart_id": cart_id, "payment": payment})

    async def emit_payment_approved(self, cart_id: str):
        await self._emit("payment_approved", {"bot_id": self._bot_id, "cart_id": cart_id})

    async def emit_payment_failed(self, cart_id: str, reason: str = ""):
        await self._emit("payment_failed", {"bot_id": self._bot_id, "cart_id": cart_id, "reason": reason})

    # ── Internals ─────────────────────────────────────────────────────────────

    async def _emit(self, event: str, data: dict):
        if not self.is_connected():
            logger.warning(f"[MarketplaceWS] Não conectado — não foi possível emitir '{event}'")
            return
        try:
            frame = "4" + "42" + json.dumps([event, data])
            await self._ws.send(frame)
        except Exception as e:
            logger.error(f"[MarketplaceWS] Erro ao emitir '{event}': {e}")
            self._connected = False

    async def _ping_loop(self, ws):
        """Envia ping Engine.IO a cada 25s para manter conexão viva."""
        try:
            while True:
                await asyncio.sleep(25)
                await ws.send("2")
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _connect_loop(self):
        while self._running:
            try:
                await self._connect_once()
            except Exception as e:
                logger.warning(f"[MarketplaceWS] Erro de conexão: {e} — tentando em 15s")
            
            self._connected = False
            if self._ping_task:
                self._ping_task.cancel()
                self._ping_task = None
            self._ws = None

            if self._running:
                await asyncio.sleep(15)

    async def _connect_once(self):
        if not (self.bot and self.bot.user):
            logger.warning("[MarketplaceWS] bot.user não disponível, tentando em 10s…")
            await asyncio.sleep(10)
            return

        self._bot_id = str(self.bot.user.id)
        secret   = _get_api_secret()
        base_url = _get_api_url()
        origin   = base_url.replace("wss://", "https://").replace("ws://", "http://")
        ws_url   = f"{base_url}/socket.io/?EIO=4&transport=websocket"

        logger.info(f"[MarketplaceWS] Conectando em {ws_url}")

        async with websockets.connect(
            ws_url,
            ping_interval=None,
            ping_timeout=None,
            open_timeout=15,
            close_timeout=10,
            additional_headers={"Origin": origin},
        ) as ws:
            self._ws = ws

            # ── 1. Receber EIO open "0{...}" ──────────────────────────────
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            if not raw.startswith("0"):
                raise Exception(f"Esperava EIO open, recebi: {raw!r}")
            logger.debug(f"[MarketplaceWS] EIO open: {raw}")

            # ── 2. Enviar SIO CONNECT com auth: "40{...}" ─────────────────
            auth = {
                "auth": {
                    "bot_id": self._bot_id,
                    "secret": secret,
                    "kind":   "bot",
                }
            }
            await ws.send("4" + "40" + json.dumps(auth))

            # ── 3. Aguardar confirmação "440" ou erro "444" ───────────────
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            logger.debug(f"[MarketplaceWS] SIO connect resp: {raw!r}")

            # raw pode ser "440" (connect ok) ou "444{...}" (erro)
            sio = raw[1:] if raw.startswith("4") else ""
            if sio.startswith("44"):
                try:
                    err = json.loads(sio[2:])
                except Exception:
                    err = sio[2:]
                raise Exception(f"Auth recusada: {err}")
            if not sio.startswith("40"):
                raise Exception(f"Resposta inesperada ao CONNECT: {raw!r}")

            logger.info("[MarketplaceWS] ✅ Conectado e autenticado!")
            self._connected = True

            # ── 4. Ping loop ──────────────────────────────────────────────
            self._ping_task = asyncio.create_task(self._ping_loop(ws))

            # ── 5. Enviar bot_connected e registrar na API ────────────────
            guilds = [str(g.id) for g in self.bot.guilds] if self.bot.guilds else []
            await self._emit("bot_connected", {"bot_id": self._bot_id, "guilds": guilds})

            # Garante que o bot está registrado na API (idempotente)
            from modules.loja.ecommerce.service import MarketplaceService
            ok, err = await MarketplaceService.ensure_registered(
                bot_id=self._bot_id,
                bot_name=str(self.bot.user.name),
            )
            if not ok:
                logger.warning(f"[MarketplaceWS] Falha ao registrar bot na API: {err}")

            # ── 6. Loop de recepção ───────────────────────────────────────
            async for raw in ws:
                await self._handle_raw(raw)

        # Saiu do async with — conexão fechada
        logger.info("[MarketplaceWS] ❌ Conexão encerrada")
        self._connected = False

    async def _handle_raw(self, raw: str):
        if not isinstance(raw, str):
            return

        if raw == "3":
            # pong — ignora
            return

        if raw == "2":
            # ping do servidor — responde com pong
            try:
                await self._ws.send("3")
            except Exception:
                pass
            return

        if not raw.startswith("4"):
            return

        sio = raw[1:]

        # "42[...]" → evento
        if sio.startswith("42"):
            try:
                arr = json.loads(sio[2:])
            except Exception:
                return
            if not isinstance(arr, list) or len(arr) < 1:
                return

            event_name = arr[0]
            data       = arr[1] if len(arr) > 1 else {}

            logger.debug(f"[MarketplaceWS] Evento recebido: {event_name}")
            await self._dispatch(event_name, data)

        # "40" → server confirmou namespace (já tratado no handshake, ignorar aqui)
        # "44" → erro tardio
        elif sio.startswith("44"):
            try:
                err = json.loads(sio[2:])
            except Exception:
                err = sio[2:]
            logger.error(f"[MarketplaceWS] Erro do servidor: {err}")
            self._connected = False

    async def _dispatch(self, event: str, data: dict):
        # Eventos internos
        if event == "auth_ok":
            logger.info(f"[MarketplaceWS] Auth OK: {data.get('message')}")
            return

        if event == "auth_error":
            logger.error(f"[MarketplaceWS] Auth FALHOU: {data.get('message')}")
            self._connected = False
            return

        if event == "ack":
            logger.debug(f"[MarketplaceWS] ACK: {data}")
            return

        # Eventos de negócio registrados via .on()
        if event in self._handlers:
            try:
                await self._handlers[event](data)
            except Exception as e:
                logger.error(f"[MarketplaceWS] Erro no handler '{event}': {e}")
                traceback.print_exc()