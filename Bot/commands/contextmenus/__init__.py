from disnake.ext import commands
from . import edit_painel_ticket
from . import edit_giveaway_panel
from . import edit_product

def setup(bot: commands.Bot):
    edit_painel_ticket.setup(bot)
    edit_giveaway_panel.setup(bot)
    edit_product.setup(bot)