import aiohttp
import asyncio
import logging
import json
from collections import deque

logger = logging.getLogger(__name__)

# ─── Instância global do gerenciador WebSocket ────────────────────────────────
websocket_manager = None

# ─── Fila e semáforo para auth_log (evita crash em pico de verificações) ─────
_auth_log_queue: asyncio.Queue = None          # inicializado em _ensure_queue()
_auth_semaphore: asyncio.Semaphore = None      # max N verificações em paralelo
_auth_worker_task: asyncio.Task = None
_MAX_CONCURRENT_AUTH = 3                       # Discord tolera ~5 req/s por bot
_AUTH_QUEUE_MAX      = 500                     # descartar se a fila estourar
_RATE_LIMIT_DELAY    = 0.3                     # segundos entre operações de cargo


def _ensure_queue():
    """Cria a fila e o semáforo na primeira chamada (event loop já deve existir)."""
    global _auth_log_queue, _auth_semaphore
    if _auth_log_queue is None:
        _auth_log_queue = asyncio.Queue(maxsize=_AUTH_QUEUE_MAX)
    if _auth_semaphore is None:
        _auth_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_AUTH)


def get_websocket_manager():
    """
    Retorna o wrapper do WSManager.
    - Eventos em tempo real (auth_log, gifts, recover) → WSManager via WebSocket.
    - Consultas do painel (auth_count, members, verification) → HTTP REST.
    """
    global websocket_manager
    if websocket_manager is None:
        try:
            from .ws_manager import WSManager
        except ImportError:
            from connections.ws_manager import WSManager

        bot_instance = get_bot_instance()
        if bot_instance:
            ws = WSManager(bot_instance)
            websocket_manager = _CloudClientWrapper(ws)
    return websocket_manager


def _get_http_base_url() -> str:
    try:
        from .cloud_config import get_cloud_url
        return get_cloud_url()
    except Exception:
        try:
            from functions.database import database as db
            config = db.obter("configs/config_websocket.json") or {}
            websocket_cfg = config.get("websocket_cloud") or {}
            return (
                websocket_cfg.get("http_url")
                or websocket_cfg.get("server_url")
                or "https://cloud.amethys.solutions"
            )
        except Exception:
            return "https://cloud.amethys.solutions"


# ─── Wrapper do WSManager ─────────────────────────────────────────────────────
# O WSManager (ws_manager.py) é WebSocket puro — correto para eventos em tempo
# real (auth_log, redeem_gift, etc.). Consultas do painel (auth_count, members,
# check-verification) agora têm rotas HTTP próprias na API (bot_query.go),
# então este wrapper as chama via HTTP sem depender do estado do WS.

class _CloudClientWrapper:
    """
    Proxy do WSManager que adiciona métodos de consulta via HTTP REST.
    - Eventos/tempo real → WSManager (WebSocket)
    - Consultas do painel → HTTP GET nas rotas /api/bot/*
    """

    def __init__(self, ws_manager):
        self._ws = ws_manager

    # ── Delegar comportamento base ────────────────────────────────────────────

    def is_connected(self) -> bool:
        return self._ws.is_connected() if self._ws else False

    def set_bot(self, bot):
        if self._ws:
            self._ws.set_bot(bot)

    def set_callbacks(self, **kwargs):
        if self._ws:
            self._ws.set_callbacks(**kwargs)

    async def start(self):
        if self._ws:
            await self._ws.start()

    async def stop(self):
        if self._ws:
            await self._ws.stop()

    async def send_message(self, event: str, data: dict) -> bool:
        if self._ws:
            return await self._ws.send_message(event, data)
        return False

    # ── Métodos WS existentes no WSManager ───────────────────────────────────

    async def register_bot(self, *a, **kw):
        return await self._ws.register_bot(*a, **kw)

    async def recover_data(self, *a, **kw):
        return await self._ws.recover_data(*a, **kw)

    async def recover_members(self, *a, **kw):
        return await self._ws.recover_members(*a, **kw)

    async def update_definitions(self, *a, **kw):
        return await self._ws.update_definitions(*a, **kw)

    async def create_gift(self, bot_id: str, gift_data: dict):
        return await self._ws.send_gift(bot_id, gift_data)

    async def update_gift(self, *a, **kw):
        return await self._ws.update_gift(*a, **kw)

    async def delete_gift(self, *a, **kw):
        return await self._ws.delete_gift(*a, **kw)

    async def delete_all_gifts(self, *a, **kw):
        return await self._ws.delete_all_gifts(*a, **kw)

    async def get_gifts(self, *a, **kw):
        return await self._ws.get_gifts(*a, **kw)

    async def list_members(self, bot_id: str) -> dict:
        """Lista membros via HTTP GET /api/bot/members"""
        return await self._http_get("/api/bot/members", {"botId": bot_id})

    # ── Consultas via HTTP (rotas adicionadas em bot_query.go) ───────────────

    async def _http_get(self, path: str, params: dict = None, timeout: int = 10) -> dict:
        import aiohttp as _aiohttp
        base = _get_http_base_url()
        url = f"{base}{path}"
        try:
            async with _aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params,
                    timeout=_aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    return {"success": False, "message": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def check_auth_count(self, bot_id: str) -> dict:
        """Contagem de autenticados via HTTP GET /api/bot/auth-count"""
        return await self._http_get("/api/bot/auth-count", {"botId": bot_id})

    async def check_user_verification(self, bot_id: str, user_id) -> dict:
        """Verifica usuário via HTTP GET /api/bot/check-verification"""
        return await self._http_get(
            "/api/bot/check-verification",
            {"botId": bot_id, "userId": str(user_id)}
        )


# ─── Worker da fila de auth_log ───────────────────────────────────────────────

async def _auth_log_worker():
    """Consome a fila _auth_log_queue um a um, respeitando o semáforo."""
    _ensure_queue()
    logger.info("[AUTH_WORKER] Worker de auth_log iniciado")
    while True:
        try:
            auth_data = await _auth_log_queue.get()
            try:
                async with _auth_semaphore:
                    await asyncio.wait_for(
                        _process_auth_log_internal(auth_data),
                        timeout=25.0,
                    )
            except asyncio.TimeoutError:
                logger.error("[AUTH_WORKER] Timeout (25 s) ao processar auth_log")
            except Exception as e:
                logger.error(f"[AUTH_WORKER] Erro ao processar auth_log: {e}")
            finally:
                _auth_log_queue.task_done()
                # Pequena pausa entre itens para não saturar a API do Discord
                await asyncio.sleep(_RATE_LIMIT_DELAY)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[AUTH_WORKER] Erro inesperado no worker: {e}")
            await asyncio.sleep(1)


def _start_auth_worker():
    """Garante que o worker está rodando (idempotente)."""
    global _auth_worker_task
    _ensure_queue()
    if _auth_worker_task is None or _auth_worker_task.done():
        try:
            loop = asyncio.get_running_loop()
            _auth_worker_task = loop.create_task(_auth_log_worker())
            logger.info("[AUTH_WORKER] Task do worker criada")
        except RuntimeError:
            logger.warning("[AUTH_WORKER] Nenhum event loop ativo — worker será criado depois")


# ─── Dedup de logs ────────────────────────────────────────────────────────────

_processed_log_ids: deque = deque(maxlen=200)   # deque é O(1) nos extremos


def _is_duplicate(log_id: str) -> bool:
    if log_id in _processed_log_ids:
        return True
    _processed_log_ids.append(log_id)
    return False


# ─── Entry-point público (chamado pelo WSManager) ─────────────────────────────

async def process_auth_log(auth_data: dict):
    """
    Enfileira o auth_log para processamento controlado.
    Não bloqueia o event loop nem cria tasks ilimitadas.
    """
    _ensure_queue()
    _start_auth_worker()

    user_data  = auth_data.get("user", {})
    user_id    = user_data.get("id")
    verified_at   = user_data.get("verified_at")
    unverified_at = user_data.get("unverified_at")
    is_revocation = unverified_at is not None
    event_type    = "revoke" if is_revocation else "verify"
    from datetime import datetime
    timestamp  = unverified_at if is_revocation else (verified_at or datetime.now().isoformat())
    log_id     = f"{user_id}_{event_type}_{timestamp}"

    if _is_duplicate(log_id):
        logger.debug(f"[AUTH_LOG] Duplicado ignorado: {log_id}")
        return

    try:
        _auth_log_queue.put_nowait(auth_data)
        logger.debug(f"[AUTH_LOG] Enfileirado ({_auth_log_queue.qsize()} na fila): {log_id}")
    except asyncio.QueueFull:
        logger.warning(
            f"[AUTH_LOG] Fila cheia ({_AUTH_QUEUE_MAX} itens) — descartando {log_id}. "
            "Considere aumentar _MAX_CONCURRENT_AUTH ou _AUTH_QUEUE_MAX."
        )


# ─── Processamento interno ────────────────────────────────────────────────────

async def _process_auth_log_internal(auth_data: dict):
    """Processa um auth_log de forma controlada (já dentro do semáforo)."""
    from . import auth_logs

    bot_instance = get_bot_instance()
    if not bot_instance:
        logger.warning("[AUTH_LOG] Bot indisponível, abortando processamento")
        return

    try:
        success, message = await asyncio.wait_for(
            auth_logs.send_auth_log(bot_instance, auth_data),
            timeout=10.0,
        )
        if not success:
            logger.error(f"[AUTH_LOG] Falha ao enviar log: {message}")
    except asyncio.TimeoutError:
        logger.error("[AUTH_LOG] Timeout ao enviar log (10 s)")
    except Exception as e:
        logger.error(f"[AUTH_LOG] Erro ao enviar log: {e}")

    user_data     = auth_data.get("user", {})
    is_revocation = "unverified_at" in user_data

    try:
        if auth_data.get("success") and not is_revocation:
            await asyncio.wait_for(give_verified_role(bot_instance, auth_data), timeout=12.0)
        else:
            await asyncio.wait_for(remove_verified_role(bot_instance, auth_data), timeout=12.0)
    except asyncio.TimeoutError:
        logger.error("[AUTH_LOG] Timeout ao alterar cargo (12 s)")
    except Exception as e:
        logger.error(f"[AUTH_LOG] Erro ao alterar cargo: {e}")


# ─── Helpers de membro (com cache) ───────────────────────────────────────────

async def _get_member_safe(guild, user_id: int):
    """
    Tenta obter o membro do cache primeiro; faz fetch apenas se necessário.
    Retorna None se não encontrar.
    """
    member = guild.get_member(user_id)
    if member:
        return member
    try:
        member = await asyncio.wait_for(guild.fetch_member(user_id), timeout=5.0)
        return member
    except asyncio.TimeoutError:
        logger.warning(f"[GET_MEMBER] Timeout ao buscar membro {user_id}")
    except Exception:
        logger.warning(f"[GET_MEMBER] Membro {user_id} não encontrado em {guild.id}")
    return None


# ─── Dar / remover cargo verificado ──────────────────────────────────────────

async def give_verified_role(bot, auth_data: dict):
    for attempt in range(3):
        try:
            await _give_verified_role_internal(bot, auth_data)
            return
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error(f"[GIVE_ROLE] Todas as tentativas falharam: {e}")
                raise


async def _give_verified_role_internal(bot, auth_data: dict):
    from functions.database import database as db

    user_data = auth_data.get("user", {})
    user_id   = user_data.get("id")
    guild_id  = auth_data.get("guild_id")

    # Fallback: usar o servidor principal configurado quando guild_id não vem no payload
    if not guild_id:
        try:
            main_server_id = db.obter("config.json").get("bot", {}).get("server")
            if main_server_id:
                guild_id = str(main_server_id)
                logger.debug(f"[GIVE_ROLE] guild_id ausente no payload — usando server principal: {guild_id}")
        except Exception as e:
            logger.warning(f"[GIVE_ROLE] Não foi possível obter server principal: {e}")

    if not user_id or not guild_id:
        logger.warning(f"[GIVE_ROLE] Dados insuficientes — user_id={user_id}, guild_id={guild_id}")
        return

    cargos_config   = db.get_document("cargos") or {}
    verified_role_id = cargos_config.get("cargo_verificado")
    if not verified_role_id:
        logger.warning("[GIVE_ROLE] cargo_verificado não configurado em 'cargos'")
        return

    guild = bot.get_guild(int(guild_id))
    if not guild:
        logger.warning(f"[GIVE_ROLE] Servidor {guild_id} não encontrado no cache do bot")
        return

    member = await _get_member_safe(guild, int(user_id))
    if not member:
        logger.warning(f"[GIVE_ROLE] Membro {user_id} não encontrado no servidor {guild_id}")
        return

    verified_role = guild.get_role(int(verified_role_id))
    if not verified_role:
        logger.warning(f"[GIVE_ROLE] Cargo {verified_role_id} não encontrado no servidor {guild_id}")
        return

    if verified_role not in member.roles:
        await member.add_roles(verified_role, reason="Verificação automática via AmyCloud")
        logger.info(f"[GIVE_ROLE] Cargo dado a {member.name} ({user_id})")
    else:
        logger.debug(f"[GIVE_ROLE] {member.name} já tem o cargo")

    # Remove autorole se configurado
    cloud_config = db.get_document("cloud_data") or {}
    definitions  = cloud_config.get("definitions", {})
    if definitions.get("remove_autorole", {}).get("enabled", False):
        autorole_id = cargos_config.get("cargo_auto_role")
        if autorole_id:
            autorole = guild.get_role(int(autorole_id))
            if autorole and autorole in member.roles:
                await asyncio.sleep(_RATE_LIMIT_DELAY)
                await member.remove_roles(autorole, reason="Remoção de autorole após verificação")
                logger.info(f"[REMOVE_AUTOROLE] Autorole removido de {member.name}")


async def remove_verified_role(bot, auth_data: dict):
    for attempt in range(3):
        try:
            await _remove_verified_role_internal(bot, auth_data)
            return
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                logger.error(f"[REMOVE_ROLE] Todas as tentativas falharam: {e}")
                raise


async def _remove_verified_role_internal(bot, auth_data: dict):
    from functions.database import database as db

    user_data = auth_data.get("user", {})
    user_id   = user_data.get("id")
    guild_id  = auth_data.get("guild_id")

    # Fallback: usar o servidor principal configurado quando guild_id não vem no payload
    if not guild_id:
        try:
            main_server_id = db.obter("config.json").get("bot", {}).get("server")
            if main_server_id:
                guild_id = str(main_server_id)
        except Exception:
            pass

    if not user_id or not guild_id:
        return

    cargos_config    = db.get_document("cargos") or {}
    verified_role_id = cargos_config.get("cargo_verificado")
    if not verified_role_id:
        return

    guild = bot.get_guild(int(guild_id))
    if not guild:
        return

    member = await _get_member_safe(guild, int(user_id))
    if not member:
        return

    verified_role = guild.get_role(int(verified_role_id))
    if not verified_role or verified_role not in member.roles:
        return

    await member.remove_roles(verified_role, reason="Desverificação automática via AmyCloud")
    logger.info(f"[REMOVE_ROLE] Cargo removido de {member.name} ({user_id})")


# ─── Outros eventos WebSocket ─────────────────────────────────────────────────

async def process_remove_verified_role(remove_data: dict):
    from functions.database import database as db

    guild_id       = remove_data.get("guild_id")
    main_server_id = db.obter("config.json").get("bot", {}).get("server")
    if guild_id and main_server_id and str(guild_id) != str(main_server_id):
        return

    user_id = remove_data.get("user_id")
    if not user_id or not guild_id:
        return

    bot_instance = get_bot_instance()
    if not bot_instance:
        return

    auth_data = {"user": {"id": user_id}, "guild_id": guild_id, "success": False}
    await remove_verified_role(bot_instance, auth_data)


async def process_redeem_gift(redeem_data: dict):
    from functions.database import database as db

    guild_id       = redeem_data.get("guildId")
    bot_id         = redeem_data.get("botId")
    cloud_config   = db.get_document("cloud_data") or {}
    bot_client_id  = cloud_config.get("client_id")
    main_server_id = db.obter("config.json").get("bot", {}).get("server")

    if bot_id and bot_client_id and str(bot_id) != str(bot_client_id):
        return
    if guild_id and main_server_id and str(guild_id) != str(main_server_id):
        return

    bot_instance = get_bot_instance()
    if not bot_instance:
        return

    guild = bot_instance.get_guild(int(guild_id))
    if not guild:
        return

    members      = redeem_data.get("members", [])
    success_count = 0
    failed_count  = 0

    sem = asyncio.Semaphore(3)

    async def _add_one(member_data):
        nonlocal success_count, failed_count
        async with sem:
            try:
                user_id      = int(member_data.get("id"))
                access_token = member_data.get("access_token")
                if not access_token or guild.get_member(user_id):
                    failed_count += 1
                    return
                ok = await add_member_to_guild(bot_instance, guild, user_id, access_token)
                if ok:
                    success_count += 1
                else:
                    failed_count += 1
                await asyncio.sleep(_RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"[REDEEM_GIFT] Erro ao adicionar membro: {e}")
                failed_count += 1

    await asyncio.gather(*[_add_one(m) for m in members])
    logger.info(f"[REDEEM_GIFT] Concluído — OK: {success_count}, Falhas: {failed_count}")


async def process_recover_members(recover_data: dict):
    from functions.database import database as db

    guild_id       = recover_data.get("guildId")
    bot_id         = recover_data.get("botId")
    cloud_config   = db.get_document("cloud_data") or {}
    bot_client_id  = cloud_config.get("client_id")
    main_server_id = db.obter("config.json").get("bot", {}).get("server")

    if bot_id and bot_client_id and str(bot_id) != str(bot_client_id):
        return
    if guild_id and main_server_id and str(guild_id) != str(main_server_id):
        return

    members       = recover_data.get("members", [])
    success_count = 0
    failed_count  = 0
    sem           = asyncio.Semaphore(3)

    async def _recover_one(member_data):
        nonlocal success_count, failed_count
        async with sem:
            try:
                user_id      = int(member_data.get("id") or member_data.get("userId"))
                access_token = member_data.get("access_token")
                if not access_token:
                    failed_count += 1
                    return
                ok = await add_member_to_guild_by_id(str(guild_id), user_id, access_token)
                if ok:
                    success_count += 1
                else:
                    failed_count += 1
                await asyncio.sleep(_RATE_LIMIT_DELAY)
            except Exception as e:
                logger.error(f"[RECOVER_MEMBERS] Erro: {e}")
                failed_count += 1

    await asyncio.gather(*[_recover_one(m) for m in members])
    logger.info(f"[RECOVER_MEMBERS] Concluído — OK: {success_count}, Falhas: {failed_count}")


# ─── Helpers HTTP ─────────────────────────────────────────────────────────────

async def add_member_to_guild(bot, guild, user_id: int, access_token: str) -> bool:
    return await add_member_to_guild_by_id(str(guild.id), user_id, access_token)


async def add_member_to_guild_by_id(guild_id: str, user_id: int, access_token: str) -> bool:
    try:
        from functions.database import database as db
        cloud_config = db.get_document("cloud_data") or {}
        bot_token    = cloud_config.get("token")
        if not bot_token:
            return False

        url     = f"https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}"
        headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.put(url, headers=headers, json={"access_token": access_token},
                                   timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status in (201, 204):
                    return True
                text = await resp.text()
                logger.error(f"[ADD_MEMBER] HTTP {resp.status} para user {user_id}: {text[:200]}")
                return False
    except Exception as e:
        logger.error(f"[ADD_MEMBER] Exceção para user {user_id}: {e}")
        return False


# ─── Inicialização e lifecycle ────────────────────────────────────────────────

async def initialize_websocket():
    from functions.database import database as db
    config           = db.obter("configs/config_websocket.json")
    websocket_config = config.get("websocket_cloud", {})

    if not websocket_config.get("auto_start", False):
        return

    _start_auth_worker()

    try:
        ws_manager   = get_websocket_manager()
        bot_instance = get_bot_instance()
        if bot_instance:
            ws_manager.set_bot(bot_instance)
        await ws_manager.start()
    except Exception as e:
        logger.error(f"[WS] Erro ao inicializar: {e}")


def register_websocket_callbacks():
    _start_auth_worker()
    try:
        ws_manager = get_websocket_manager()
        bot_instance = get_bot_instance()
        if bot_instance:
            ws_manager.set_bot(bot_instance)

        async def on_message(message_data):
            event = message_data.get("event")
            data  = message_data.get("data", {})
            if event == "auth_log":
                await process_auth_log(data)
            elif event == "redeem_gift":
                asyncio.create_task(process_redeem_gift(data))
            elif event == "recover_members":
                asyncio.create_task(process_recover_members(data))
            elif event == "remove_verified_role":
                asyncio.create_task(process_remove_verified_role(data))

        ws_manager.set_callbacks(
            on_connect=None,
            on_disconnect=None,
            on_error=None,
            on_message=on_message,
        )
    except Exception as e:
        logger.error(f"[WS] Erro ao registrar callbacks: {e}")


async def stop_websocket():
    global websocket_manager
    if websocket_manager:
        await websocket_manager.stop()


# ─── Bot instance ─────────────────────────────────────────────────────────────

_bot_instance = None


def set_bot_instance(bot):
    global _bot_instance
    _bot_instance = bot
    global websocket_manager
    if websocket_manager:
        websocket_manager.set_bot(bot)
    else:
        try:
            from .ws_manager import WSManager
        except ImportError:
            from connections.ws_manager import WSManager
        websocket_manager = _CloudClientWrapper(WSManager(bot))


def get_bot_instance():
    return _bot_instance


# ─── Registro / recuperação de bot ───────────────────────────────────────────

async def register_bot(main_bot_id: str, bot_token: str, client_secret: str,
                        verified_role_id: str, log_channel_id: str,
                        auto_role_id: str = None) -> tuple[bool, str, dict]:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": f"Bot {bot_token}"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return False, "Token do bot inválido.", {}
            bot_info  = await resp.json()
            client_id = bot_info["id"]
            bot_name  = bot_info["username"]

    ws_manager = get_websocket_manager()
    if ws_manager and ws_manager.is_connected():
        try:
            response = await ws_manager.register_bot(main_bot_id, bot_token, client_secret, client_id)
            if response.get("success"):
                from functions.database import database as db
                main_server_id = db.obter("config.json").get("bot", {}).get("server")
                return True, response.get("message", "Bot registrado!"), {
                    "client_id": client_id, "client_secret": client_secret,
                    "token": bot_token, "name": bot_name, "main_server_id": main_server_id,
                }
            return False, response.get("message", "Erro ao registrar"), {}
        except Exception as e:
            logger.warning(f"[REGISTER] WS falhou, tentando HTTP: {e}")

    try:
        cloud_url = _get_http_base_url()
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{cloud_url}/api/bot/register",
                json={"token": bot_token, "clientSecret": client_secret,
                      "clientId": client_id, "mainBotId": main_bot_id},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        from functions.database import database as db
                        main_server_id = db.obter("config.json").get("bot", {}).get("server")
                        return True, data.get("message", "Bot registrado via HTTP!"), {
                            "client_id": client_id, "client_secret": client_secret,
                            "token": bot_token, "name": bot_name, "main_server_id": main_server_id,
                        }
                    return False, data.get("message", "Erro"), {}
                return False, f"HTTP {resp.status}", {}
    except Exception as e:
        return False, f"Erro: {e}", {}


async def recover_bot_data(bot_id: str, recovery_data: dict = None) -> tuple[bool, str, dict]:
    ws_manager = get_websocket_manager()
    if ws_manager and ws_manager.is_connected():
        try:
            response = await ws_manager.recover_data(bot_id)
            if response.get("success"):
                return True, "Dados recuperados!", response.get("data", {})
            return False, response.get("message", "Erro"), {}
        except Exception as e:
            logger.warning(f"[RECOVER] WS falhou, tentando HTTP: {e}")

    try:
        cloud_url = _get_http_base_url()
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{cloud_url}/api/bot/recover",
                params={"botId": bot_id},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("success"):
                        return True, "Dados recuperados via HTTP!", data.get("data", {})
                    return False, data.get("message", "Erro"), {}
                return False, f"HTTP {resp.status}", {}
    except Exception as e:
        return False, f"Erro: {e}", {}


async def start_recover_members(server_id: str, concurrency: int = None,
                                 base_delay_ms: int = None) -> dict:
    try:
        from functions.database import database as db
        cloud_config  = db.get_document("cloud_data") or {}
        client_id     = cloud_config.get("client_id")
        client_secret = cloud_config.get("client_secret")
        token         = cloud_config.get("token")

        if not client_id or not client_secret or not token:
            return {"success": False, "message": "Credenciais incompletas"}

        base_url = _get_http_base_url()
        payload  = {"data": {"client_id": client_id, "client_secret": client_secret,
                             "token": token, "server_id": str(server_id)}}
        if concurrency is not None:
            payload["data"]["concurrency"] = int(concurrency)
        if base_delay_ms is not None:
            payload["data"]["baseDelayMs"] = int(base_delay_ms)

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{base_url}/api/recover/members", json=payload,
                                    timeout=aiohttp.ClientTimeout(total=30)) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text) if text else {}
                except Exception:
                    data = {}
                if 200 <= resp.status < 300:
                    return {"success": True,
                            "message": (data.get("message") if isinstance(data, dict) else None) or "Started",
                            "data": (data.get("data") if isinstance(data, dict) else {})}
                return {"success": False,
                        "message": (data.get("message") if isinstance(data, dict) else text) or f"HTTP {resp.status}",
                        "data": {}}
    except Exception as e:
        return {"success": False, "message": f"Erro: {e}"}


async def get_recovery_status(recovery_id: str) -> dict:
    try:
        base_url = _get_http_base_url()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/api/recover/status/{recovery_id}",
                                   timeout=aiohttp.ClientTimeout(total=15)) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text) if text else {}
                except Exception:
                    data = {}
                if 200 <= resp.status < 300:
                    return {"success": True,
                            "data": (data.get("data") if isinstance(data, dict) else {}),
                            "message": (data.get("message") if isinstance(data, dict) else None)}
                return {"success": False,
                        "message": (data.get("message") if isinstance(data, dict) else text) or f"HTTP {resp.status}",
                        "data": {}}
    except Exception as e:
        return {"success": False, "message": f"Erro: {e}"}