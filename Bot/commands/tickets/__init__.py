from disnake.ext import commands
from . import setup as setup_module
from . import ticket

def setup(bot: commands.Bot):
    """Loads the ticket cogs."""
    setup_module.setup(bot)
    ticket.setup(bot)