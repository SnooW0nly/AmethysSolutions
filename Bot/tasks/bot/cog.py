import disnake
import asyncio
from disnake.ext import commands
from .status_rotator import status_rotator_task
from .change_bio_task import change_bio_task
from .bio_monitor_task import bio_monitor_task
from .cargo_temporario_task import CargoTemporarioTaskCog
import core

class StatusRotatorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._bio_updated_once = False

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        if not status_rotator_task.is_running():
            status_rotator_task.start(self.bot)
        else:
            status_rotator_task.restart(self.bot)
        
        # Atualiza a bio imediatamente ao ligar o bot
        if not self._bio_updated_once:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, core.change_bio)
                print("Bio atualizada ao iniciar o bot")
                self._bio_updated_once = True
            except Exception as e:
                print(f"Erro ao atualizar bio ao iniciar: {e}")
        
        # Inicia a task de atualização de bio a cada 1 hora
        if not change_bio_task.is_running():
            change_bio_task.start(self.bot)
        
        # Inicia a task de monitoramento de bio a cada 1 minuto
        if not bio_monitor_task.is_running():
            bio_monitor_task.start(self.bot)

        # Inicia a task de remoção de cargos temporários expirados
        if not hasattr(self.bot, '_cargo_temp_cog'):
            self.bot._cargo_temp_cog = CargoTemporarioTaskCog(self.bot)
            self.bot.add_cog(self.bot._cargo_temp_cog)

def setup(bot: commands.Bot):
    bot.add_cog(StatusRotatorCog(bot))
