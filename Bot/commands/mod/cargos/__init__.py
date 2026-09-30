from disnake.ext import commands
from .add import Add
from .remove import Remove

def setup(bot: commands.Bot):
    bot.add_cog(Add(bot))
    bot.add_cog(Remove(bot))
