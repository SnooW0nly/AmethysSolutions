from disnake.ext import commands
from .actions import CargosCampoActions


def setup(bot: commands.Bot):
    bot.add_cog(CargosCampoActions(bot))


__all__ = ["setup"]


