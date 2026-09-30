from disnake.ext import commands

from . import giveaway

def setup(bot: commands.Bot):
    giveaway.setup(bot)