import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.message import message, embed_message
from .config.config_ticket import PainelTicket_components, PainelTicket_embed


class TicketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def display_ticket_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
            embed, components = PainelTicket_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await message.wait(inter, send=False)
            components = PainelTicket_components(inter)
            await inter.edit_original_message(components=components)


def setup(bot: commands.Bot):
    bot.add_cog(TicketCog(bot))
