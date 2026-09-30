import disnake
from disnake.ext import commands

from functions.database import database as db
from modules.giveaways.config_giveaways import SpecificGiveawayView_components, SpecificGiveawayView_embed
from functions.message import embed_message
from functions.perms import perms
from functions.emoji import emoji


class EditGiveawayPanelContextMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.message_command(name="Editar Sorteio")
    async def edit_giveaway_panel(self, inter: disnake.MessageInteraction):
        await embed_message.wait(inter, send=True)

        if not await perms.check(inter.user.id):
            return await inter.edit_original_response(
                content=f"{emoji.wrong} Você não tem permissão para usar este comando"
            )

        target_message_id = inter.target.id

        config = db.get_document("giveaways_data") or {}
        
        giveaway_id_found = None
        
        for giveaway_id, giveaway_data in config.items():
            for task in giveaway_data.get("tasks", []):
                if task.get("message_id") == target_message_id:
                    giveaway_id_found = giveaway_id
                    break
            if giveaway_id_found:
                break

        if giveaway_id_found:
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                components = SpecificGiveawayView_components(inter, giveaway_id_found)
                await inter.edit_original_response(content=None, components=components)
            else:
                embed, components = SpecificGiveawayView_embed(inter, giveaway_id_found)
                await inter.edit_original_response(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_response(
                content=f"{emoji.wrong} Esta mensagem não é um sorteio configurado."
            )


def setup(bot):
    bot.add_cog(EditGiveawayPanelContextMenu(bot))
