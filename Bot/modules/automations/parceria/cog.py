from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path

import aiohttp
import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db

log = logging.getLogger("parcerias")

# ══════════════════════════════════════════════════════════════════════════════
# Constantes
# ══════════════════════════════════════════════════════════════════════════════

PARC_DB_KEY    = "parcerias_config"
_MENTION_RE    = re.compile(r"@everyone|@here|<@&\d+>", re.IGNORECASE)
_BASE_ENDPOINT = "/api/partnerships"


# ══════════════════════════════════════════════════════════════════════════════
# Config helpers
# ══════════════════════════════════════════════════════════════════════════════

def _get_config() -> dict:
    return db.get_document(PARC_DB_KEY) or {}


def _save_config(data: dict):
    atual = _get_config()
    atual.update(data)
    db.save_document(PARC_DB_KEY, atual)


def _get_msg() -> str:
    return _get_config().get("message", "") or ""


def _save_msg(text: str):
    _save_config({"message": text})


def _load_api_url() -> str:
    """Lê a URL base da API de configs/config_api.json (mesmo padrão do Tools)."""
    try:
        path = Path("configs/config_api.json")
        if not path.exists():
            path = Path(__file__).parent.parent.parent / "configs" / "config_api.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("parcerias") or data.get("url") or "http://localhost:3000"
    except Exception:
        return "http://localhost:3000"


def _load_bot_config() -> dict:
    try:
        path = Path("config.json")
        if not path.exists():
            path = Path(__file__).parent.parent.parent / "config.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _bot_id() -> str:
    cfg = _load_bot_config()
    return str(cfg.get("botID") or cfg.get("bot", {}).get("id", ""))


def _server_id() -> str:
    cfg = _load_bot_config()
    return str(cfg.get("bot", {}).get("server", ""))


# ══════════════════════════════════════════════════════════════════════════════
# Sanitização
# ══════════════════════════════════════════════════════════════════════════════

def _sanitize(text: str) -> str:
    return _MENTION_RE.sub("[bloqueado]", text)


def _has_mention(text: str) -> bool:
    return bool(_MENTION_RE.search(text))


# ══════════════════════════════════════════════════════════════════════════════
# Painéis (Components v2 — inline)
# ══════════════════════════════════════════════════════════════════════════════

def _ck() -> dict:
    colors = db.get_document("custom_colors")
    hex_   = (colors or {}).get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


def get_parcerias_main(config: dict) -> list:
    ativo     = config.get("ativo", False)
    canal_id  = config.get("canal_id") or "Não configurado"
    intervalo = config.get("intervalo_min", 60)
    mensagem  = _sanitize(config.get("message", "") or "")
    tem_msg   = bool(mensagem)

    s_icon = emoji.correct if ativo   else emoji.wrong
    s_text = "Ativo"       if ativo   else "Inativo"
    m_icon = emoji.correct if tem_msg else emoji.wrong
    m_text = "Configurada" if tem_msg else "Não configurada"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Painel > Extensões > **Parcerias**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                "Sistema de parcerias automáticas entre bots.\n"
                "Cadastra seu bot na rede global e envia mensagens de parceria automaticamente."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**Status:** {s_icon} `{s_text}`\n"
                f"**Canal de envio:** `{canal_id}`\n"
                f"**Intervalo:** `{intervalo} minuto(s)`\n"
                f"**Mensagem:** {m_icon} `{m_text}`"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Desativar" if ativo else "Ativar",
                    style=disnake.ButtonStyle.red if ativo else disnake.ButtonStyle.green,
                    emoji=emoji.wrong if ativo else emoji.correct,
                    custom_id="Parc_Toggle",
                ),
                disnake.ui.Button(
                    label="Canal",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="Parc_SetCanal",
                ),
                disnake.ui.Button(
                    label="Intervalo",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="Parc_SetIntervalo",
                ),
                disnake.ui.Button(
                    label="Mensagem",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="Parc_SetMensagem",
                ),
            ),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="Extensions_Select_Back",
            ),
        ),
    ]


def get_parcerias_resultado(sucesso: bool, mensagem: str, back_id: str) -> list:
    icon   = emoji.correct if sucesso else emoji.wrong
    titulo = "Sucesso" if sucesso else "Erro"
    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                f"-# Parcerias — {titulo}"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(f"**# {icon} {titulo.upper()}**\n> {mensagem}"),
            **_ck(),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id=back_id,
            ),
        ),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# API client
# ══════════════════════════════════════════════════════════════════════════════

class ParceriasAPI:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _base(self) -> str:
        return _load_api_url().rstrip("/") + _BASE_ENDPOINT

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        session = await self._get_session()
        url = self._base() + path
        async with session.request(method, url, **kwargs) as resp:
            text = await resp.text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = {"raw": text}
            if resp.status >= 400:
                raise RuntimeError(data.get("error", f"HTTP {resp.status}"))
            return data

    async def register(self, bot_id: str, server_id: str) -> dict:
        try:
            return await self._request("POST", f"/bots/{bot_id}/register", json={"serverId": server_id})
        except RuntimeError as e:
            if "already registered" in str(e).lower():
                return {}
            raise

    async def configure(self, bot_id: str, channel_id: str | None = None,
                        message: str | None = None, role_id: str | None = None) -> dict:
        body: dict = {}
        if channel_id is not None:
            body["channelId"] = channel_id
        if message is not None:
            body["message"] = message
        if role_id is not None:
            body["roleId"] = role_id
        return await self._request("PATCH", f"/bots/{bot_id}/config", json=body)

    async def toggle(self, bot_id: str) -> dict:
        return await self._request("PATCH", f"/bots/{bot_id}/toggle")

    async def list_active(self) -> list[dict]:
        data = await self._request("GET", "/bots/active")
        return data.get("bots", [])

    async def confirm(self, bot_id: str, target_bot_id: str) -> dict:
        return await self._request("POST", f"/bots/{bot_id}/confirm", json={"targetBotId": target_bot_id})

    async def list_partnerships(self, bot_id: str) -> dict:
        return await self._request("GET", f"/bots/{bot_id}/partnerships")


api = ParceriasAPI()


# ══════════════════════════════════════════════════════════════════════════════
# WebSocket listener
# ══════════════════════════════════════════════════════════════════════════════

class ParceriasWS:
    def __init__(self, bot: commands.Bot):
        self.bot      = bot
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self):
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.get_event_loop().create_task(
            self._connect_loop(), name="tsk_parcerias_ws"
        )

    def cancel(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _connect_loop(self):
        await self.bot.wait_until_ready()
        backoff = 5
        while self._running:
            try:
                await self._listen()
                backoff = 5
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning(f"[ParceriasWS] Desconectado: {e}. Reconectando em {backoff}s…")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _listen(self):
        bot_id  = _bot_id()
        base    = _load_api_url().rstrip("/")
        ws_url  = base.replace("http://", "ws://").replace("https://", "wss://")
        ws_url += f"/ws?botId={bot_id}"

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url) as ws:
                log.info(f"[ParceriasWS] Conectado botId={bot_id}")
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await self._handle_ws_event(msg.data)
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        break

    async def _handle_ws_event(self, raw: str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return

        event = payload.get("event")
        data  = payload.get("data", {})

        if event == "bot.configured":
            changes = data.get("changes", {})
            update: dict = {}
            if "channelId" in changes:
                update["canal_id"] = changes["channelId"]
            if "message" in changes:
                update["message"] = changes["message"]
            if update:
                _save_config(update)

        elif event == "bot.toggled":
            _save_config({"ativo": data.get("globalEnabled", False)})

        elif event == "partnership.confirmed":
            log.info(f"[ParceriasWS] Parceria confirmada com {data.get('targetBotId', '?')}")


# ══════════════════════════════════════════════════════════════════════════════
# Task: tsk_parcerias
# ══════════════════════════════════════════════════════════════════════════════

class ParceriasTask:
    def __init__(self, bot: commands.Bot):
        self.bot      = bot
        self._task: asyncio.Task | None = None
        self._running = False

    def start(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self._running = True
        self._task = asyncio.get_event_loop().create_task(
            self._loop(), name="tsk_parcerias"
        )
        log.info("[tsk_parcerias] Iniciada.")

    def stop(self):
        self._running = False
        log.info("[tsk_parcerias] Parada.")

    def cancel(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    @property
    def is_running(self) -> bool:
        return bool(self._task and not self._task.done() and self._running)

    async def _loop(self):
        await self.bot.wait_until_ready()
        while self._running:
            try:
                await self._cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"[tsk_parcerias] Erro: {e}", exc_info=True)

            config    = _get_config()
            intervalo = max(1, int(config.get("intervalo_min", 60)))
            for _ in range(intervalo * 60):
                if not self._running:
                    return
                await asyncio.sleep(1)

    async def _cycle(self):
        config = _get_config()
        if not config.get("ativo", False):
            return

        bot_id    = _bot_id()
        msg_local = _sanitize(_get_msg())

        if not bot_id or not msg_local:
            return

        try:
            ativos = await api.list_active()
        except Exception as e:
            log.error(f"[tsk_parcerias] Falha ao listar ativos: {e}")
            return

        ja_parceiros: set[str] = set()
        try:
            data = await api.list_partnerships(bot_id)
            for p in data.get("partnerships", []):
                for sid in p.get("servers", {}).keys():
                    ja_parceiros.add(sid)
        except Exception:
            pass

        ja_parceiros.discard(_server_id())

        for candidato in ativos:
            c_bot_id    = candidato.get("botId", "")
            c_server_id = candidato.get("serverId", "")
            c_channel   = candidato.get("channelId")

            if c_bot_id == bot_id:
                continue
            if c_server_id in ja_parceiros:
                continue
            if not c_channel:
                continue

            try:
                channel = self.bot.get_channel(int(c_channel))
                if channel is None:
                    channel = await self.bot.fetch_channel(int(c_channel))
                await channel.send(
                    content=msg_local,
                    allowed_mentions=disnake.AllowedMentions.none(),
                )
                log.info(f"[tsk_parcerias] Mensagem enviada canal {c_channel}")
            except Exception as e:
                log.error(f"[tsk_parcerias] Erro ao enviar canal {c_channel}: {e}")
                continue

            try:
                await api.confirm(bot_id, c_bot_id)
                ja_parceiros.add(c_server_id)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    log.warning(f"[tsk_parcerias] Falha confirmar {c_bot_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Modals
# ══════════════════════════════════════════════════════════════════════════════

class CanalModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Configurar Canal de Parceria",
            custom_id="Parc_CanalModal",
            components=[
                disnake.ui.TextInput(
                    label="ID do Canal",
                    custom_id="canal_id",
                    placeholder="Cole o ID do canal onde a parceria será enviada",
                    style=disnake.TextInputStyle.short,
                    max_length=30,
                    required=True,
                    value=_get_config().get("canal_id", "") or "",
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        canal_id = inter.text_values["canal_id"].strip()
        if not canal_id.isdigit():
            await inter.response.edit_message(
                components=get_parcerias_resultado(False, "O ID do canal deve conter apenas números.", "Parc_Main"),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        try:
            await api.configure(_bot_id(), channel_id=canal_id)
        except Exception as e:
            log.warning(f"[Parcerias] Falha ao sincronizar canal com API: {e}")

        _save_config({"canal_id": canal_id})
        await inter.response.edit_message(
            components=get_parcerias_main(_get_config()),
            flags=disnake.MessageFlags(is_components_v2=True),
        )


class IntervaloModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Configurar Intervalo de Envio",
            custom_id="Parc_IntervaloModal",
            components=[
                disnake.ui.TextInput(
                    label="Intervalo em minutos (mínimo: 1)",
                    custom_id="intervalo_min",
                    placeholder="Ex: 60",
                    style=disnake.TextInputStyle.short,
                    max_length=5,
                    required=True,
                    value=str(_get_config().get("intervalo_min", 60)),
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        raw = inter.text_values["intervalo_min"].strip()
        try:
            intervalo = max(1, int(raw))
        except ValueError:
            await inter.response.edit_message(
                components=get_parcerias_resultado(False, "Digite um número inteiro de minutos.", "Parc_Main"),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        _save_config({"intervalo_min": intervalo})
        await inter.response.edit_message(
            components=get_parcerias_main(_get_config()),
            flags=disnake.MessageFlags(is_components_v2=True),
        )


class MensagemModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Editar Mensagem de Parceria",
            custom_id="Parc_MensagemModal",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem",
                    custom_id="message",
                    placeholder=(
                        "Mensagem enviada nos servidores parceiros.\n"
                        "@everyone, @here e cargos são bloqueados automaticamente."
                    ),
                    style=disnake.TextInputStyle.paragraph,
                    max_length=2000,
                    required=True,
                    value=_get_msg(),
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        raw  = inter.text_values["message"].strip()
        text = _sanitize(raw)

        if not text:
            await inter.response.edit_message(
                components=get_parcerias_resultado(False, "A mensagem não pode ficar vazia.", "Parc_Main"),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
            return

        try:
            await api.configure(_bot_id(), message=text)
        except Exception as e:
            log.warning(f"[Parcerias] Falha ao sincronizar mensagem com API: {e}")

        _save_msg(text)

        if _has_mention(raw):
            await inter.response.edit_message(
                components=get_parcerias_resultado(
                    True,
                    "Mensagem salva.\n-# ⚠️ Menções proibidas foram removidas automaticamente.",
                    "Parc_Main",
                ),
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        else:
            await inter.response.edit_message(
                components=get_parcerias_main(_get_config()),
                flags=disnake.MessageFlags(is_components_v2=True),
            )


# ══════════════════════════════════════════════════════════════════════════════
# Cog
# ══════════════════════════════════════════════════════════════════════════════

class ParceriasCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot   = bot
        self._ws   = ParceriasWS(bot)
        self._task = ParceriasTask(bot)

        config = _get_config()
        if config.get("ativo", False):
            self._task.start()
        self._ws.start()

    def cog_unload(self):
        self._task.cancel()
        self._ws.cancel()
        asyncio.create_task(api.close())

    @commands.Cog.listener("on_ready")
    async def handle_ready(self):
        bot_id    = _bot_id()
        server_id = _server_id()
        if not bot_id or not server_id:
            log.warning("[Parcerias] botId ou serverId não encontrado em config.json")
            return
        try:
            await api.register(bot_id, server_id)
            log.info(f"[Parcerias] Registrado (botId={bot_id})")
            config  = _get_config()
            canal   = config.get("canal_id")
            message = _sanitize(config.get("message", "") or "")
            if canal or message:
                await api.configure(bot_id, channel_id=canal or None, message=message or None)
        except Exception as e:
            log.error(f"[Parcerias] Erro no registro: {e}")

    @commands.Cog.listener("on_message_interaction")
    async def handle_parcerias(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id

        if cid == "Parc_Main":
            await inter.response.edit_message(
                components=get_parcerias_main(_get_config()),
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        elif cid == "Parc_Toggle":
            config = _get_config()
            novo   = not config.get("ativo", False)

            if novo:
                if not config.get("canal_id"):
                    await inter.response.edit_message(
                        components=get_parcerias_resultado(False, "Configure o **canal** antes de ativar.", "Parc_Main"),
                        flags=disnake.MessageFlags(is_components_v2=True),
                    )
                    return
                if not _get_msg():
                    await inter.response.edit_message(
                        components=get_parcerias_resultado(False, "Configure a **mensagem** antes de ativar.", "Parc_Main"),
                        flags=disnake.MessageFlags(is_components_v2=True),
                    )
                    return

            try:
                result = await api.toggle(_bot_id())
                novo   = result.get("bot", {}).get("globalEnabled", novo)
            except Exception as e:
                log.warning(f"[Parcerias] Falha ao sincronizar toggle com API: {e}")

            _save_config({"ativo": novo})
            if novo:
                self._task.start()
            else:
                self._task.stop()

            await inter.response.edit_message(
                components=get_parcerias_main(_get_config()),
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        elif cid == "Parc_SetCanal":
            await inter.response.send_modal(CanalModal())

        elif cid == "Parc_SetIntervalo":
            await inter.response.send_modal(IntervaloModal())

        elif cid == "Parc_SetMensagem":
            await inter.response.send_modal(MensagemModal())


def setup(bot: commands.Bot):
    bot.add_cog(ParceriasCog(bot))