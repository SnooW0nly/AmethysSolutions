"""
tasks/automations/tsk_auto_role_avancado.py

Task periódica que verifica membros para gatilhos que não são em tempo real:
  - tempo_servidor : verifica a cada hora membros que atingiram o limiar de dias
  - tempo_call     : verificação extra a cada 15min
  - convites       : re-verifica a cada 30min
"""
from __future__ import annotations

import asyncio

import disnake
from disnake.ext import commands, tasks

from modules.automations.auto_role_avancado.helpers import (
    carregar_config,
    regras_por_tipo,
    aplicar_regras_membro,
)


class AutoRoleAvancadoTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._tsk_tempo_servidor.is_running():
            self._tsk_tempo_servidor.start()
        if not self._tsk_tempo_call.is_running():
            self._tsk_tempo_call.start()
        if not self._tsk_convites.is_running():
            self._tsk_convites.start()

    def cog_unload(self):
        self._tsk_tempo_servidor.cancel()
        self._tsk_tempo_call.cancel()
        self._tsk_convites.cancel()

    # ── Tempo no servidor — a cada 1 hora ─────────────────────────────────────

    @tasks.loop(hours=1)
    async def _tsk_tempo_servidor(self):
        config = carregar_config()
        if not config.get("ativado", False):
            return
        if not regras_por_tipo(config, "tempo_servidor"):
            return

        for guild in self.bot.guilds:
            for membro in guild.members:
                if membro.bot:
                    continue
                try:
                    await aplicar_regras_membro(membro, self.bot, tipos_verificar=["tempo_servidor"])
                    await asyncio.sleep(0.15)
                except Exception:
                    pass

    @_tsk_tempo_servidor.before_loop
    async def _before_ts(self):
        await self.bot.wait_until_ready()

    # ── Tempo em call — a cada 15 minutos ────────────────────────────────────

    @tasks.loop(minutes=15)
    async def _tsk_tempo_call(self):
        config = carregar_config()
        if not config.get("ativado", False):
            return
        if not regras_por_tipo(config, "tempo_call"):
            return

        for guild in self.bot.guilds:
            for membro in guild.members:
                if membro.bot:
                    continue
                try:
                    await aplicar_regras_membro(membro, self.bot, tipos_verificar=["tempo_call"])
                    await asyncio.sleep(0.1)
                except Exception:
                    pass

    @_tsk_tempo_call.before_loop
    async def _before_tc(self):
        await self.bot.wait_until_ready()

    # ── Convites — a cada 30 minutos ─────────────────────────────────────────

    @tasks.loop(minutes=30)
    async def _tsk_convites(self):
        config = carregar_config()
        if not config.get("ativado", False):
            return
        if not regras_por_tipo(config, "convites"):
            return

        for guild in self.bot.guilds:
            for membro in guild.members:
                if membro.bot:
                    continue
                try:
                    await aplicar_regras_membro(membro, self.bot, tipos_verificar=["convites"])
                    await asyncio.sleep(0.15)
                except Exception:
                    pass

    @_tsk_convites.before_loop
    async def _before_conv(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(AutoRoleAvancadoTask(bot))