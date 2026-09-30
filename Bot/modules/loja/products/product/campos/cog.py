import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from .fields.configurar import ConfigurarCampo
from .panels import build_components, build_embed
from functions.loja_products import get_products


class GerenciarCamposCategorias(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def panel(self, inter: disnake.MessageInteraction, product_id: str):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return self._panel_embed(inter, product_id)
        return self._panel_components(inter, product_id)

    def _panel_components(self, inter: disnake.MessageInteraction, product_id: str) -> dict:
        products = get_products()
        product = products.get(product_id) or {}
        return build_components(product, product_id)

    def _panel_embed(self, inter: disnake.MessageInteraction, product_id: str) -> dict:
        products = get_products()
        product = products.get(product_id) or {}
        return build_embed(product, product_id)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        if custom_id.startswith("Loja_CamposProduto:"):
            _, product_id = custom_id.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel_data = self.panel(inter, product_id)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        elif custom_id.startswith("Loja_CamposProduto_Voltar:"):
            _, product_id = custom_id.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel_data = self.panel(inter, product_id)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        
        if custom_id.startswith("Loja_Campos_Select:"):
            product_id = custom_id.split(":", 1)[1]
            field_id = inter.values[0]
            if field_id == "disabled":
                return

            mode = db.get_document("custom_mode").get("mode")
            panel_data = ConfigurarCampo.panel(inter, product_id, field_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)


def setup(bot: commands.Bot):
    bot.add_cog(GerenciarCamposCategorias(bot))


