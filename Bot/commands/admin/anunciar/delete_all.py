import disnake
from disnake.ext import commands

from functions.database import database
from functions.message import message
from .anunciar import Anunciar


class DeleteAll(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_ApagarTudo":
            await message.wait(inter, send=False)
            db = database.get_document("messages_anunciar")
            db["message"]["content"]       = None
            db["message"]["container"]     = None
            db["message"]["externalImage"] = None
            db["message"]["audio"]         = None
            db["message"]["buttons"]       = []
            db["message"]["selects"]       = []          # ← NEW
            for key in db["message"]["embed"]:
                db["message"]["embed"][key] = None
            database.save_document("messages_anunciar", {}, db)
            await inter.edit_original_message(components=Anunciar.create_buttons())


def setup(bot: commands.Bot):
    bot.add_cog(DeleteAll(bot))