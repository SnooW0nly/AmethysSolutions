"""
tsk_ranking_publico.py
-----------------------
Task de atualização em tempo real do Ranking Público.

- Roda em loop com intervalo configurável (padrão: 5 minutos).
- Reatualiza o intervalo da task dinamicamente toda vez que o loop executa,
  respeitando o valor salvo em ranking_publico > intervalo_minutos.
- Após cada compra aprovada, o módulo de checkout pode chamar
  `RankingPublicoTask.trigger_update()` para forçar atualização imediata.
- Faz edit na mensagem existente; se a mensagem foi deletada, envia nova
  e salva o novo message_id.
"""

import asyncio

import disnake
from disnake.ext import commands, tasks

from functions.database import database as db
from modules.loja.preferences.ranking_publico import (
    _get_config,
    _save_config,
    send_or_update_ranking,
)

# Intervalo mínimo aceito (segundos) para evitar rate-limit de edição
_MIN_INTERVAL_SECONDS = 60


class RankingPublicoTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._pending_update = asyncio.Event()
        self._update_loop.start()
        self._watcher_loop.start()

    def cog_unload(self):
        self._update_loop.cancel()
        self._watcher_loop.cancel()

    # ──────────────────────────────────────────────────────────────────────────
    # API pública: forçar atualização imediata (chamada após compra aprovada)
    # ──────────────────────────────────────────────────────────────────────────

    @classmethod
    def trigger_update(cls, bot: commands.Bot) -> None:
        """
        Força uma atualização imediata do ranking após um evento relevante
        (ex: compra aprovada, avaliação submetida).

        Uso em checkout.py / delivery.py:
            from tasks.loja.tsk_ranking_publico import RankingPublicoTask
            RankingPublicoTask.trigger_update(bot)
        """
        cog: "RankingPublicoTask | None" = bot.get_cog("RankingPublicoTask")
        if cog:
            cog._pending_update.set()

    # ──────────────────────────────────────────────────────────────────────────
    # Loop principal: atualiza no intervalo configurado
    # ──────────────────────────────────────────────────────────────────────────

    @tasks.loop(seconds=_MIN_INTERVAL_SECONDS)
    async def _update_loop(self):
        await self._run_update()

    @_update_loop.before_loop
    async def _before_update_loop(self):
        await self.bot.wait_until_ready()
        # Aguarda 10s após ready para outros cogs carregarem
        await asyncio.sleep(10)

    # ──────────────────────────────────────────────────────────────────────────
    # Watcher: escuta trigger_update e age imediatamente
    # ──────────────────────────────────────────────────────────────────────────

    @tasks.loop(seconds=5)
    async def _watcher_loop(self):
        """Verifica se há uma atualização pendente (disparada por trigger_update)."""
        if self._pending_update.is_set():
            self._pending_update.clear()
            await self._run_update(forced=True)

    @_watcher_loop.before_loop
    async def _before_watcher_loop(self):
        await self.bot.wait_until_ready()

    # ──────────────────────────────────────────────────────────────────────────
    # Lógica central de atualização
    # ──────────────────────────────────────────────────────────────────────────

    async def _run_update(self, forced: bool = False) -> None:
        cfg = _get_config()

        if not cfg.get("enabled", False):
            return

        channel_id = cfg.get("channel_id")
        if not channel_id:
            return

        # Ajustar intervalo do loop dinamicamente
        intervalo_min = cfg.get("intervalo_minutos", 5)
        intervalo_sec = max(intervalo_min * 60, _MIN_INTERVAL_SECONDS)
        if self._update_loop.seconds != intervalo_sec:
            try:
                self._update_loop.change_interval(seconds=intervalo_sec)
            except Exception:
                pass  # Pode falhar se o loop não estiver em estado correto

        # Buscar guild
        guild = self._get_guild(channel_id)
        if not guild:
            return

        try:
            msg_id = await send_or_update_ranking(self.bot, cfg, guild)
            if msg_id and msg_id != cfg.get("message_id"):
                cfg["message_id"] = msg_id
                _save_config(cfg)
            if forced:
                print(f"[RANKING PÚBLICO] Atualização forçada concluída (canal: {channel_id})")
        except Exception as e:
            print(f"[RANKING PÚBLICO] Erro na atualização: {e}")

    def _get_guild(self, channel_id: int) -> disnake.Guild | None:
        """Encontra o guild que contém o canal configurado."""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if channel and hasattr(channel, "guild"):
                return channel.guild
        except Exception:
            pass

        # Fallback: primeiro guild disponível (bot em um único servidor)
        if self.bot.guilds:
            return self.bot.guilds[0]
        return None


def setup(bot: commands.Bot):
    bot.add_cog(RankingPublicoTask(bot))