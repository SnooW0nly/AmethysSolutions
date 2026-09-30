import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from ..cog import GerenciarProdutos


class DeleteProduct(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        # Esperado: "Loja_ApagarProduto:<product_id>"
        if custom_id and custom_id.startswith("Loja_ApagarProduto"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return

            # Deleta o produto do arquivo JSON
            products = db.get_document("loja_products")
            if product_id in products:
                del products[product_id]
                db.save_document("loja_products", products)

            # Volta ao painel de gerenciamento de produtos
            mode = db.get_document("custom_mode").get("mode")
            panel_builder = GerenciarProdutos(self.bot)
            panel_data = panel_builder.panel(inter)

            if mode == "embed":
                await embed_message.wait(inter, send=False)
                # Quando embed, removemos o content e passamos o embed/components
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                # Para components v2, usamos a flag apropriada
                if "embed" in panel_data:
                    await inter.edit_original_message(**panel_data)
                else:
                    await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))


def setup(bot: commands.Bot):
    bot.add_cog(DeleteProduct(bot))


