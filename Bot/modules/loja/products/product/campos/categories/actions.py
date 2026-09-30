import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message

from .modals import CreateCategoryModal, EditCategoryModal
from .configurar import ConfigurarCategoria
from ..cog import GerenciarCamposCategorias


class CategoryActions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        if custom_id.startswith("Loja_CriarCategoria:"):
            product_id = custom_id.split(":", 1)[1]
            modal = CreateCategoryModal(product_id)
            await inter.response.send_modal(modal)
            return

        if custom_id.startswith("Loja_EditarCategoria:"):
            _, rest = custom_id.split(":", 1)
            product_id, category_id = rest.split(":", 1)
            modal = EditCategoryModal(product_id, category_id)
            await inter.response.send_modal(modal)
            return

        if custom_id.startswith("Loja_ApagarCategoria:"):
            _, rest = custom_id.split(":", 1)
            product_id, category_id = rest.split(":", 1)
            await message.wait(inter, send=False)

            products = db.get_document("loja_products")
            product = products.get(product_id) or {}
            categorias = product.get("categorias") or {}
            if category_id in categorias:
                categorias.pop(category_id, None)
                # Remover vínculo de campos
                campos = product.get("campos") or {}
                for campo in campos.values():
                    if campo.get("category_id") == category_id:
                        campo["category_id"] = None
                product["campos"] = campos
                product["categorias"] = categorias
                products[product_id] = product
                db.save_document("loja_products", products)

            mode = db.get_document("custom_mode").get("mode")
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, product_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)


def setup(bot: commands.Bot):
    bot.add_cog(CategoryActions(bot))


