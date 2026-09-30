from disnake.ext import commands
from .cog import Cloud

def setup(bot: commands.Bot):
    bot.add_cog(Cloud(bot))

__all__ = ["setup"]