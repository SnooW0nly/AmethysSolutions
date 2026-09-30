import disnake
from disnake.ext import commands
from functions.database import database
from functions.message import message
from ..anunciar import Anunciar

class Message(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class DefinirMensagemModal(disnake.ui.Modal):
        def __init__(self):
            db = database.get_document("messages_anunciar")
            self.db = db
            super().__init__(
                title="Definir Mensagem",
                custom_id="Anunciar_DefinirMensagemModal",
                components=[
                    disnake.ui.TextInput(
                        label="Mensagem",
                        custom_id="message",
                        style=disnake.TextInputStyle.paragraph,
                        placeholder="Digite a mensagem que deseja anunciar",
                        value=self.db["message"]["content"] if self.db["message"]["content"] else "",
                        max_length=2000,
                        required=True
                    )
                ],
            )
        
        async def callback(self, inter: disnake.ModalInteraction):
            await message.wait(inter, send=False)
            db = database.get_document("messages_anunciar")
            db["message"]["content"] = inter.text_values["message"]
            database.save_document("messages_anunciar", {}, db)
            await inter.edit_original_message(components=Anunciar.create_buttons())

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_DefinirMensagem":
            await inter.response.send_modal(self.DefinirMensagemModal())
        
        if inter.component.custom_id == "Anunciar_ApagarMensagem":
            await message.wait(inter, send=False)
            db = database.get_document("messages_anunciar")
            db["message"]["content"] = None
            database.save_document("messages_anunciar", {}, db)
            await inter.edit_original_message(components=Anunciar.create_buttons())
