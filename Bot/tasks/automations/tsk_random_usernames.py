"""
tasks/utilitarios/tsk_random_usernames.py

Task periódica que:
  1. Verifica se o sistema de Random Usernames está ativo.
  2. Lê os comprimentos habilitados (2l sempre, 3l e 4l pelos toggles).
  3. Gera lotes e testa disponibilidade via Discord API (Full HTTPS).
  4. Para cada username disponível, envia no canal configurado para aquele
     comprimento com o username em content + timestamp Unix.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import disnake
from disnake.ext import commands

from functions.database import database as db

from modules.automations.random_usernames.helpers import (
    ler_config,
    comprimentos_ativos,
    canais_por_comprimento,
)
from modules.automations.random_usernames.functions import (
    escanear_usernames,
    filtrar_disponiveis,
)

log = logging.getLogger(__name__)

_CICLO_SEGUNDOS = 45
_QTDE_POR_COMP  = 15
_DELAY_REQUEST  = 1.3


def _get_token() -> Optional[str]:
    doc    = db.get_document("tokens") or {}
    tokens = doc.get("list", [])
    return tokens[0]["token"] if tokens else None


class RandomUsernamesTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot      = bot
        self._task:   Optional[asyncio.Task] = None
        self._running = False

    async def cog_load(self):
        cfg = ler_config()
        if cfg.get("ativado") and _get_token():
            self._iniciar_task()
        log.info("[RandomUsernames] Task cog carregado.")

    def cog_unload(self):
        self._parar_task()
        log.info("[RandomUsernames] Task cog descarregado.")

    def _iniciar_task(self):
        if self._task and not self._task.done():
            return
        self._running = True
        self._task    = asyncio.create_task(self._loop(), name="random_usernames_loop")
        log.debug("[RandomUsernames] Task iniciada.")

    def _parar_task(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
        log.debug("[RandomUsernames] Task encerrada.")

    async def _loop(self):
        await self.bot.wait_until_ready()
        log.debug("[RandomUsernames] Loop iniciado.")

        while self._running:
            try:
                cfg = ler_config()

                if not cfg.get("ativado"):
                    log.info("[RandomUsernames] Desativado. Encerrando loop.")
                    self._task = None
                    return

                token = _get_token()
                if not token:
                    log.warning("[RandomUsernames] Sem token. Aguardando.")
                    await asyncio.sleep(_CICLO_SEGUNDOS)
                    continue

                mapa_canais  = canais_por_comprimento(cfg)
                comps_cfg    = comprimentos_ativos(cfg)
                # Só escaneia comprimentos que têm canal configurado
                comps_validos = [c for c in comps_cfg if mapa_canais.get(c)]

                if not comps_validos:
                    log.info("[RandomUsernames] Nenhum comprimento com canal. Aguardando.")
                    await asyncio.sleep(_CICLO_SEGUNDOS)
                    continue

                repeat = bool(cfg.get("toggle_rep", False))

                log.debug("[RandomUsernames] Escaneando comps=%s repeat=%s", comps_validos, repeat)

                resultados  = await escanear_usernames(
                    token=token,
                    comprimentos_ativos=comps_validos,
                    repeat=repeat,
                    quantidade_por_comprimento=_QTDE_POR_COMP,
                    delay_entre_requests=_DELAY_REQUEST,
                )
                disponiveis = filtrar_disponiveis(resultados)

                log.info(
                    "[RandomUsernames] %d testados / %d disponíveis.",
                    len(resultados), len(disponiveis),
                )

                if disponiveis:
                    await self._enviar_resultados(disponiveis, mapa_canais)

                await asyncio.sleep(_CICLO_SEGUNDOS)

            except asyncio.CancelledError:
                log.debug("[RandomUsernames] Loop cancelado.")
                return
            except Exception:
                log.exception("[RandomUsernames] Erro no loop. Retentando em 30s.")
                await asyncio.sleep(30)

    async def _enviar_resultados(self, disponiveis: list[dict], mapa_canais: dict[int, str | None]):
        ts = int(time.time())

        for item in disponiveis:
            username    = item["username"]
            comprimento = item["comprimento"]
            canal_id    = mapa_canais.get(comprimento)

            if not canal_id:
                continue

            canal = await self._resolver_canal(canal_id)
            if canal is None:
                log.warning("[RandomUsernames] Canal %s não encontrado.", canal_id)
                continue

            conteudo = f"`{username}` ({comprimento}l) — encontrado <t:{ts}:R>"

            try:
                await canal.send(content=conteudo)
                log.debug("[RandomUsernames] Enviado '%s' → #%s.", username, canal_id)
            except disnake.Forbidden:
                log.warning("[RandomUsernames] Sem permissão em %s.", canal_id)
            except disnake.HTTPException as e:
                log.warning("[RandomUsernames] HTTP error em %s: %s", canal_id, e)
            except Exception:
                log.exception("[RandomUsernames] Erro ao enviar em %s.", canal_id)

            await asyncio.sleep(0.4)

    async def _resolver_canal(self, canal_id: str) -> Optional[disnake.TextChannel]:
        try:
            canal = self.bot.get_channel(int(canal_id))
            if canal is None:
                canal = await self.bot.fetch_channel(int(canal_id))
            return canal if isinstance(canal, disnake.TextChannel) else None
        except Exception:
            return None

    @commands.Cog.listener("on_button_click")
    async def _watch_toggle(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "RU:toggle_sistema":
            return
        await asyncio.sleep(0.3)
        cfg = ler_config()
        if cfg.get("ativado") and _get_token():
            self._iniciar_task()
        else:
            self._parar_task()


def setup(bot: commands.Bot):
    bot.add_cog(RandomUsernamesTask(bot))