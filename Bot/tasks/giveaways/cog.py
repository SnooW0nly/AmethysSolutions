import disnake
from disnake.ext import commands
from .monitor_giveaway import monitor_giveaways_task
from .roll_giveaways import roll_giveaways_task

class GiveawaysTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not monitor_giveaways_task.is_running():
            monitor_giveaways_task.start(self.bot)
        if not roll_giveaways_task.is_running():
            roll_giveaways_task.start(self.bot)

    def cog_unload(self):
        monitor_giveaways_task.cancel()
        roll_giveaways_task.cancel()

def setup(bot: commands.Bot):
    bot.add_cog(GiveawaysTasks(bot))