import disnake
from disnake.ext import commands, tasks
import asyncio
from typing import Dict

from modules.automations.cont_members_call import helpers

NORMAL_MODE_INTERVAL_SECONDS = 120
FAST_MODE_INTERVAL_SECONDS = 60
FAST_MODE_DURATION_SECONDS = 600

class ContMembrosCallTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._update_task: asyncio.Task | None = None
        self._guild_last_run_at: Dict[int, float] = {}
        self._guild_fast_mode_until: Dict[int, float] = {}
        self._scheduler_tick_seconds: int = 15

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

                now = loop.time()
                for guild in self.bot.guilds:
                    interval = FAST_MODE_INTERVAL_SECONDS if now < self._guild_fast_mode_until.get(guild.id, 0.0) else NORMAL_MODE_INTERVAL_SECONDS
                    if now - self._guild_last_run_at.get(guild.id, 0.0) >= interval:
                        try:
                            await self.atualizar_todos_contadores(guild)
                        finally:
                            self._guild_last_run_at[guild.id] = loop.time()
                await asyncio.sleep(self._scheduler_tick_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Erro no loop de atualização do ContMembrosCall: {e}")
                await asyncio.sleep(5)

    async def atualizar_todos_contadores(self, guild: disnake.Guild):
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return
            
        membros_em_call = helpers.contar_membros_em_call(guild)
        estilo = config.get("estilo", 0)

        for contador in config.get("contadores", []):
            if contador.get("guild_id") == guild.id:
                try:
                    novo_nome = helpers.formatar_nome_contador(contador.get('prefixo', 'Em Call'), membros_em_call, estilo)
                    target = guild.get_channel(contador["target_id"])
                    if target and (isinstance(target, (disnake.VoiceChannel, disnake.CategoryChannel))):
                        if target.name != novo_nome:
                            await target.edit(name=novo_nome, reason="Atualização automática do contador")
                except disnake.HTTPException:
                    continue # Ignora erros de rate limit ou permissão
    
    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(self, member, before, after):
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return
        
        loop = asyncio.get_running_loop()
        self._guild_fast_mode_until[member.guild.id] = loop.time() + FAST_MODE_DURATION_SECONDS
        self._ensure_update_task_running()

def setup(bot: commands.Bot):
    bot.add_cog(ContMembrosCallTaskCog(bot))
