from disnake.ext import commands
from .cog import NitroAutomaticoCog

def setup(bot: commands.Bot):
    bot.add_cog(NitroAutomaticoCog(bot))

__all__ = ["setup"]
