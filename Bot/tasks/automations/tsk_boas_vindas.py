import asyncio
import time
from collections import deque

import disnake
from disnake.ext import commands

from modules.automations.boas_vindas import helpers
from commands.admin.anunciar.builder import Builder


class BoasVindasTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._send_semaphore = asyncio.Semaphore(10)
        self._dm_semaphore = asyncio.Semaphore(3)
        self._dm_lock = asyncio.Lock()
        self._dm_window_seconds = 60
        self._dm_max_per_window = 20
        self._dm_timestamps = deque()

    # ── Controle de rate limit para DM ────────────────────────────────────────

    async def _try_acquire_dm_slot(self) -> bool:
        agora = time.time()
        async with self._dm_lock:
            while self._dm_timestamps and (agora - self._dm_timestamps[0]) > self._dm_window_seconds:
                self._dm_timestamps.popleft()
            if len(self._dm_timestamps) >= self._dm_max_per_window:
                return False
            self._dm_timestamps.append(agora)
            return True

    # ── Construir cfg compatível com o Builder ─────────────────────────────────

    @staticmethod
    def _build_cfg_for_rota(rota: str, member: disnake.Member) -> dict:
        """
        Pega o editor_data da rota, formata as variáveis {user} etc e
        devolve um dict no formato que o Builder do anunciar espera:
        {"message": {...}} com content, embed, container, buttons, externalImage.
        """
        editor_data = helpers.get_editor_data(rota)

        def _fmt(text: str | None) -> str | None:
            if not text:
                return text
            return helpers.formatar_mensagem(text, member)

        # Copia profunda mínima do editor_data para não sujar o banco
        msg: dict = {}

        if editor_data.get("content"):
            msg["content"] = _fmt(editor_data["content"])

        if editor_data.get("embed"):
            embed_raw = editor_data["embed"]
            msg["embed"] = {
                "title": _fmt(embed_raw.get("title")),
                "description": _fmt(embed_raw.get("description")),
                "color": embed_raw.get("color"),
                "footer": _fmt(embed_raw.get("footer")),
                "banner": embed_raw.get("banner"),
                "thumbnail": embed_raw.get("thumbnail"),
            }

        if editor_data.get("container"):
            msg["container"] = _fmt(editor_data["container"])

        if editor_data.get("externalImage"):
            msg["externalImage"] = editor_data["externalImage"]

        # Converte "botoes" → "buttons" (mesmo padrão do MsgAuto)
        botoes = editor_data.get("botoes") or []
        if botoes:
            # Substitui o custom_id para usar o prefixo de boas-vindas
            buttons = []
            for b in botoes:
                btn_copy = dict(b)
                btn_copy["id"] = b.get("id", "")
                buttons.append(btn_copy)
            msg["buttons"] = buttons
        else:
            msg["buttons"] = []

        return {"message": msg}

    # ── Envio de mensagem via Builder ─────────────────────────────────────────

    async def _enviar_para_canal(self, canal: disnake.TextChannel, cfg_msg: dict, tempo: int) -> None:
        """Constrói e envia a mensagem de boas-vindas no canal."""
        built = await Builder.build_from_cfg(cfg_msg)

        if built["mode"] == "v2":
            msg = await canal.send(
                components=built["components"],
                flags=built["flags"],
                allowed_mentions=disnake.AllowedMentions.none(),
            )
        else:
            kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
            if built.get("content"):
                kwargs["content"] = built["content"]
            if built.get("embed"):
                kwargs["embed"] = built["embed"]
            if built.get("components"):
                kwargs["components"] = built["components"]
            if built.get("files"):
                kwargs["files"] = built["files"]
            msg = await canal.send(**kwargs)

        # Adiciona o badge de sistema se não for v2
        if built["mode"] != "v2":
            try:
                pass  # badge pode ser adicionado se desejado
            except Exception:
                pass

        # Apaga após N segundos se configurado
        if msg and tempo > 0:
            async def _apagar(m: disnake.Message, s: int):
                try:
                    await asyncio.sleep(max(1, s))
                    await m.delete()
                except Exception:
                    pass
            asyncio.create_task(_apagar(msg, tempo))

    async def _enviar_para_dm(self, member: disnake.Member, cfg_msg: dict) -> None:
        """Constrói e envia a mensagem de boas-vindas na DM do membro."""
        try:
            dm = await member.create_dm()
        except Exception:
            return

        try:
            built = await Builder.build_from_cfg(cfg_msg)
        except Exception:
            return

        try:
            if built["mode"] == "v2":
                await dm.send(
                    components=built["components"],
                    flags=built["flags"],
                    allowed_mentions=disnake.AllowedMentions.none(),
                )
            else:
                kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
                if built.get("content"):
                    kwargs["content"] = built["content"]
                if built.get("embed"):
                    kwargs["embed"] = built["embed"]
                if built.get("components"):
                    kwargs["components"] = built["components"]
                if built.get("files"):
                    kwargs["files"] = built["files"]
                await dm.send(**kwargs)
        except Exception:
            return

    # ── Ghost Ping ────────────────────────────────────────────────────────────

    async def _enviar_ghost_ping(self, member: disnake.Member, config: dict) -> None:
        if not bool(config.get("ghost_ping_ativo", False)):
            return
        canais_ids = config.get("ghost_ping_canais") or []
        if not canais_ids:
            return
        guild = member.guild

        async def _ghost_em_canal(canal_id: int) -> None:
            canal = guild.get_channel(canal_id)
            if not isinstance(canal, disnake.TextChannel):
                return
            try:
                msg = await canal.send(member.mention)
                await asyncio.sleep(2.5)
                await msg.delete()
            except Exception:
                pass

        tasks = []
        for raw_id in canais_ids:
            try:
                tasks.append(asyncio.create_task(_ghost_em_canal(int(raw_id))))
            except Exception:
                continue
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # ── Lógica principal ──────────────────────────────────────────────────────

    async def _enviar_boas_vindas(self, member: disnake.Member) -> None:
        if not member or not getattr(member, "guild", None):
            return

        config = helpers.carregar_config()
        if not bool(config.get("ativado", True)):
            return

        rota = str(config.get("rota_envio", "canal"))
        tempo = int(config.get("canal", {}).get("tempo_segundos", 0) or 0)

        # ── Canal ──
        if rota in ("canal", "canal_dm"):
            canal_cfg = self._build_cfg_for_rota("canal", member)
            # Verifica se há conteúdo
            msg_canal = canal_cfg.get("message", {})
            has_content = any([
                msg_canal.get("content"),
                msg_canal.get("embed"),
                msg_canal.get("container"),
                msg_canal.get("externalImage"),
            ])
            if has_content:
                canal = helpers.obter_canal_boas_vindas(member.guild)
                if canal:
                    async with self._send_semaphore:
                        tentativa = 0
                        while tentativa < 3:
                            try:
                                await self._enviar_para_canal(canal, canal_cfg, tempo)
                                break
                            except Exception:
                                await asyncio.sleep(0.5 * (2 ** tentativa))
                                tentativa += 1

        # ── DM ──
        if rota in ("dm", "canal_dm"):
            dm_cfg = self._build_cfg_for_rota("dm", member)
            msg_dm = dm_cfg.get("message", {})
            has_content_dm = any([
                msg_dm.get("content"),
                msg_dm.get("embed"),
                msg_dm.get("container"),
                msg_dm.get("externalImage"),
            ])
            if has_content_dm and await self._try_acquire_dm_slot():
                async with self._dm_semaphore:
                    await self._enviar_para_dm(member, dm_cfg)

        # ── Ghost Ping ──
        await self._enviar_ghost_ping(member, config)

    @commands.Cog.listener()
    async def on_member_join(self, member: disnake.Member):
        try:
            await self._enviar_boas_vindas(member)
        except Exception:
            return


def setup(bot: commands.Bot):
    bot.add_cog(BoasVindasTask(bot))