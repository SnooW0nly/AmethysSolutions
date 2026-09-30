import disnake
from disnake.ext import commands
from functions.database import database
from functions.message import message
from ..anunciar import Anunciar

class Embed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class DefinirEmbedModal(disnake.ui.Modal):
        def __init__(self):
            db = database.get_document("messages_anunciar")
            self.db = db
            
            super().__init__(
                title="Definir Embed",
                custom_id="Anunciar_DefinirEmbedModal",
                components=[
                    disnake.ui.TextInput(
                        label="Título",
                        custom_id="Anunciar_Titulo",
                        style=disnake.TextInputStyle.short,
                        required=False,
                        placeholder="Digite o título do embed",
                        value=self.db["message"]["embed"]["title"] if self.db["message"]["embed"]["title"] else "",
                    ),
                    disnake.ui.TextInput(
                        label="Descrição",
                        custom_id="Anunciar_Descricao",
                        style=disnake.TextInputStyle.paragraph,
                        placeholder="Digite a descrição do embed",
                        required=True,
                        value=self.db["message"]["embed"]["description"] if self.db["message"]["embed"]["description"] else "",
                    ),
                    disnake.ui.TextInput(
                        label="Cor ― Hexadecimal",
                        custom_id="Anunciar_Cor",
                        style=disnake.TextInputStyle.short,
                        required=False,
                        placeholder="Digite a cor do embed (Exemplo: #000000)",
                        value=self.db["message"]["embed"]["color"] if self.db["message"]["embed"]["color"] else "",
                    ),
                    disnake.ui.TextInput(
                        label="Footer",
                        custom_id="Anunciar_Footer",
                        style=disnake.TextInputStyle.short,
                        required=False,
                        placeholder="Digite o footer do embed",
                        value=self.db["message"]["embed"]["footer"] if self.db["message"]["embed"]["footer"] else "",
                    ),
                ]
            )

        async def callback(self, inter: disnake.ModalInteraction):
            await message.wait(inter, send=False)
            db = database.get_document("messages_anunciar")

            def validar_hex(codigo: str) -> str | None:
                codigo = codigo.strip()
                if codigo.startswith("#"): codigo = codigo[1:]
                if len(codigo) not in (3, 6): return None
                
                try: int(codigo, 16)
                except ValueError: return None
                return codigo.upper()

            db["message"]["embed"]["title"] = inter.text_values.get("Anunciar_Titulo", None)
            db["message"]["embed"]["description"] = inter.text_values.get("Anunciar_Descricao", None)
            db["message"]["embed"]["color"] = validar_hex(inter.text_values.get("Anunciar_Cor", None))
            db["message"]["embed"]["footer"] = inter.text_values.get("Anunciar_Footer", None)
            database.save_document("messages_anunciar", {}, db)
            await inter.edit_original_message(components=Anunciar.create_buttons())


    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_DefinirEmbed":
            await inter.response.send_modal(self.DefinirEmbedModal())
        
        elif inter.component.custom_id == "Anunciar_ApagarEmbed":
            db = database.get_document("messages_anunciar")
            for key in db["message"]["embed"]: db["message"]["embed"][key] = None
            database.save_document("messages_anunciar", {}, db)
            await inter.response.edit_message(components=Anunciar.create_buttons())

def setup(bot: commands.Bot):
    bot.add_cog(Embed(bot))
