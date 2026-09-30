from disnake.ext import commands
from .cog import MarketplaceCog


def setup(bot: commands.Bot):
    bot.add_cog(MarketplaceCog(bot))


__all__ = ["setup"]