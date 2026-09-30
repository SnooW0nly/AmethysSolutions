import disnake
from disnake.ext import commands

from functions.database import database
from functions.message import message
from .helper import Helper
from ..anunciar import Anunciar

class Container(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class ContainerModal(disnake.ui.Modal):
        def __init__(self):
            db = database.get_document("messages_anunciar")
            self.db = db
            super().__init__(
                title="Definir Container",
                custom_id="Anunciar_ContainerModal",
                components=[
                    disnake.ui.TextInput(
                        label="Conteúdo do container", 
                        style=disnake.TextInputStyle.paragraph, 
                        custom_id="Anunciar_Container", 
                        placeholder="Se precisar de ajuda para criar, digite /ajuda aqui", 
                        required=True, 
                        value=self.db["message"]["container"] if self.db["message"]["container"] else ""
                    ),
                ]
            )
        
        async def callback(self, inter: disnake.ModalInteraction):
            if inter.text_values["Anunciar_Container"] == "/ajuda":
                return await inter.response.send_message(components=Helper.helper("example"), ephemeral=True, flags=disnake.MessageFlags(is_components_v2=True))

            await message.wait(inter, send=False)
            db = database.get_document("messages_anunciar")
            db["message"]["container"] = inter.text_values["Anunciar_Container"]
            database.save_document("messages_anunciar", {}, db)
            await inter.edit_original_message(components=Anunciar.create_buttons())
            return

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_DefinirContainer":
            await inter.response.send_modal(self.ContainerModal())
        
        elif inter.component.custom_id == "Anunciar_ApagarContainer":
            await message.wait(inter, send=False)
            db = database.get_document("messages_anunciar")
            db["message"]["container"] = None
            database.save_document("messages_anunciar", {}, db)
            await inter.edit_original_message(components=Anunciar.create_buttons())