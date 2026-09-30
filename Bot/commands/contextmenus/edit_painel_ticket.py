import disnake
from disnake.ext import commands

from functions.database import database as db
from modules.tickets.config.edit_panel import SpecificPanelView_components, SpecificPanelView_embed
from functions.message import embed_message
from functions.perms import perms
from functions.emoji import emoji


class EditTicketPanelContextMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.message_command(name="Editar Painel do Ticket")
    async def edit_ticket_panel(self, inter: disnake.MessageInteraction):
        await embed_message.wait(inter, send=True)

        if not await perms.check(inter.user.id):
            return await inter.edit_original_response(
                content=f"{emoji.wrong} Você não tem permissão para usar este comando"
            )

        target_message_id = inter.target.id

        config = db.get_document("tickets_config") or {}
        panels = config.get("panels", {})

        panel_id_found = None
        for panel_id, panel_data in panels.items():
            if panel_data.get("message_id") == target_message_id:
                panel_id_found = panel_id
                break

        if panel_id_found:
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                components = SpecificPanelView_components(inter, panel_id_found)
                await inter.edit_original_response(content=None, components=components)
            else:
                embed, components = SpecificPanelView_embed(inter, panel_id_found)
                await inter.edit_original_response(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_response(
                content=f"{emoji.wrong} Esta mensagem não é um painel de ticket configurado."
            )


def setup(bot):
    bot.add_cog(EditTicketPanelContextMenu(bot))
