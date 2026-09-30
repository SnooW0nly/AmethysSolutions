"""
tasks/loja/tsk_marketplace_cache.py
────────────────────────────────────
Mantém o cache do marketplace sempre quente em background.
O cog.py do marketplace nunca faz query ao MongoDB na hora —
apenas lê do cache em memória que esta task atualiza.

IMPORTANTE — por que asyncio.to_thread?
─────────────────────────────────────────
fetch_resale_products() usa pymongo síncrono e faz N+1 queries ao
MongoDB (1 para listar collections + 1 por bot).  Chamar isso
diretamente dentro de uma coroutine bloqueia o event loop do asyncio,
impedindo que o heartbeat do Discord Gateway seja enviado no prazo
(~41 s) e causando desconexões.

asyncio.to_thread() executa a função em uma thread do ThreadPoolExecutor
do asyncio, liberando o event loop completamente durante a I/O.
"""

import asyncio

import disnake
from disnake.ext import commands, tasks

from functions.marketplace import fetch_resale_products


class MarketplaceCacheTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Startup ──────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_ready")
    async def on_ready(self) -> None:
        await self.bot.wait_until_ready()

        # Migração do estoque.json → MongoDB (I/O de arquivo + possível DB)
        # Executada em thread para não travar o startup do bot.
        try:
            from modules.loja.cart.stock_manager import StockManager
            await asyncio.to_thread(StockManager._load_stock)
        except Exception as e:
            print(f"[MarketplaceCache] Erro ao migrar estoque: {e}")

        # Aquece o cache antes de liberar a task periódica.
        # Também em thread — pode demorar conforme quantidade de bots no banco.
        try:
            await asyncio.to_thread(fetch_resale_products, force_refresh=True)
            print("[MarketplaceCache] Cache aquecido com sucesso.")
        except Exception as e:
            print(f"[MarketplaceCache] Erro no aquecimento inicial: {e}")

        if not self._refresh_cache.is_running():
            self._refresh_cache.start()

    # ── Task periódica ───────────────────────────────────────────────────────

    def cog_unload(self) -> None:
        self._refresh_cache.cancel()

    @tasks.loop(seconds=60)
    async def _refresh_cache(self) -> None:
        """
        Atualiza o cache a cada 60 s sem bloquear o event loop.

        asyncio.to_thread() executa fetch_resale_products() em uma thread
        separada.  O event loop permanece livre para processar heartbeats,
        interações e qualquer outro evento enquanto a query ao MongoDB ocorre.
        """
        try:
            await asyncio.to_thread(fetch_resale_products, force_refresh=True)
        except Exception as e:
            print(f"[MarketplaceCache] Erro ao atualizar cache: {e}")

    @_refresh_cache.before_loop
    async def _before_refresh(self) -> None:
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot) -> None:
    bot.add_cog(MarketplaceCacheTask(bot))