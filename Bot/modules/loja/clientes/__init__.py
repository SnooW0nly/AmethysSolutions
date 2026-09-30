from disnake.ext import commands
from .cog import ClientesSystem

def setup(bot: commands.Bot):
    bot.add_cog(ClientesSystem(bot))