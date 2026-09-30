from disnake.ext import commands
from .cog import RendimentosSystem

def setup(bot: commands.Bot):
    bot.add_cog(RendimentosSystem(bot))