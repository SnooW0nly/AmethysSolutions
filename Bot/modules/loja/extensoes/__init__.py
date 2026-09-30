from disnake.ext import commands

from .cog import setup as extensoes_cog_setup
from .roblox import setup as roblox_setup
from .gerador import setup as gerador_setup
from .joiner import setup as joiner_setup
from .auto_nitrada import setup as auto_nitrada_setup

def setup(bot: commands.Bot):
    extensoes_cog_setup(bot)
    roblox_setup(bot)
    gerador_setup(bot)
    joiner_setup(bot)
    auto_nitrada_setup(bot)