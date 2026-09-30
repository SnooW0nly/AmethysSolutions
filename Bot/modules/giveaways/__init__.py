from disnake.ext import commands
from .cog import Giveaways

def setup(bot: commands.Bot):
    bot.add_cog(Giveaways(bot))

__all__ = ["setup"]