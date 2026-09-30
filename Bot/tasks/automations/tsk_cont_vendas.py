import disnake
from disnake.ext import commands, tasks
import asyncio
from typing import Dict

from modules.automations.cont_vendas import helpers

NORMAL_MODE_INTERVAL_SECONDS = 300  # 5 minutos
FAST_MODE_INTERVAL_SECONDS = 60  # 1 minuto após uma venda
FAST_MODE_DURATION_SECONDS = 600  # 10 minutos em modo rápido

class ContVendasTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._update_task: asyncio.Task | None = None
        self._guild_last_run_at: Dict[int, float] = {}
        self._guild_fast_mode_until: Dict[int, float] = {}
        self._scheduler_tick_seconds: int = 30

    @commands.Cog.listener()
    async def on_ready(self):
        """Inicia o loop de atualização quando o bot estiver pronto."""
        self._ensure_update_task_running()

    def cog_unload(self):
        self._stop_update_task()

    def _ensure_update_task_running(self):
        if self._update_task is None or self._update_task.done():
            self._update_task = asyncio.create_task(self._update_loop())

    def _stop_update_task(self):
        if self._update_task and not self._update_task.done():
            self._update_task.cancel()
        self._update_task = None

    async def _update_loop(self):
        await self.bot.wait_until_ready()
        loop = asyncio.get_running_loop()
        while True:
            try:
                config = helpers.carregar_config()
                if not config.get("ativado", False):
                    await asyncio.sleep(30)
                    continue

                # Contar todas as vendas uma vez (globalmente)
                todas_vendas_count = helpers.contar_todas_vendas(bot=self.bot)
                estilo = config.get("estilo", 0)

                now = loop.time()
                for guild in self.bot.guilds:
                    interval = FAST_MODE_INTERVAL_SECONDS if now < self._guild_fast_mode_until.get(guild.id, 0.0) else NORMAL_MODE_INTERVAL_SECONDS
                    if now - self._guild_last_run_at.get(guild.id, 0.0) >= interval:
                        try:
                            await self.atualizar_todos_contadores(guild, todas_vendas_count, estilo)
                        finally:
                            self._guild_last_run_at[guild.id] = loop.time()
                await asyncio.sleep(self._scheduler_tick_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Erro no loop de atualização do ContVendas: {e}")
                await asyncio.sleep(5)

    async def atualizar_todos_contadores(self, guild: disnake.Guild, vendas_count: int = None, estilo: int = None):
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return
        
        # Se não foram fornecidos, calcular globalmente
        if vendas_count is None:
            vendas_count = helpers.contar_todas_vendas(bot=self.bot)
        if estilo is None:
            estilo = config.get("estilo", 0)

        for contador in config.get("contadores", []):
            if contador.get("guild_id") == guild.id:
                try:
                    novo_nome = helpers.formatar_nome_contador(contador.get('prefixo', 'Vendas'), vendas_count, estilo)
                    target = guild.get_channel(contador["target_id"])
                    if target and (isinstance(target, (disnake.VoiceChannel, disnake.CategoryChannel))):
                        if target.name != novo_nome:
                            await target.edit(name=novo_nome, reason="Atualização automática do contador de vendas")
                except disnake.HTTPException:
                    continue  # Ignora erros de rate limit ou permissão
    
    @commands.Cog.listener("on_button_click")
    async def on_purchase_completed(self, inter: disnake.MessageInteraction):
        """Ativa modo rápido quando uma compra é completada"""
        # Verificar se é um botão relacionado a compras (se houver)
        # Por enquanto, vamos usar um listener genérico que pode ser chamado manualmente
        pass
    
    def trigger_fast_mode(self, guild_id: int):
        """Ativa modo rápido para um servidor após uma venda"""
        loop = asyncio.get_running_loop()
        self._guild_fast_mode_until[guild_id] = loop.time() + FAST_MODE_DURATION_SECONDS
        self._ensure_update_task_running()

def setup(bot: commands.Bot):
    bot.add_cog(ContVendasTaskCog(bot))

