import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from functions.utils import utils
from functions.loja_products import validate_emoji_string
from ..cog import GerenciarCamposCategorias
from .configurar import ConfigurarCategoria

class CreateCategoryModal(disnake.ui.Modal):
    def __init__(self, product_id: str):
        self.product_id = product_id

        components = [
            disnake.ui.Label(
                text="Nome da categoria",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: Acessórios",
                    custom_id="category_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    # Create modal: no cat context
                ),
            ),
            disnake.ui.Label(
                text="Emoji (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: 🔧 ou <:custom:123>",
                    custom_id="category_emoji",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    # Create modal: no cat context
                ),
            ),
            disnake.ui.Label(
                text="Pré-descrição (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Breve descrição para exibição nos menus",
                    custom_id="category_pre_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    # Create modal: no cat context
                ),
            ),
            disnake.ui.Label(
                text="Descrição (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Descrição detalhada da categoria",
                    custom_id="category_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    # Create modal: no cat context
                ),
            ),
        ]

        super().__init__(title="Criar Categoria", components=components, custom_id=f"create_category_modal:{product_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        valores = inter.resolved_values
        name = valores.get("category_name")
        emoji_str = validate_emoji_string(inter.bot, valores.get("category_emoji"))
        pre_desc = valores.get("category_pre_description")
        desc = valores.get("category_description")

        now_ts = int(disnake.utils.utcnow().timestamp())

        products = db.get_document("loja_products")
        product = products.get(self.product_id) or {}
        categorias = product.get("categorias") or {}

        category_id = utils.gerar_id()
        categorias[category_id] = {
            "id": category_id,
            "name": name,
            "emoji": emoji_str,
            "pre_description": pre_desc,
            "description": desc,
            "created_at": now_ts,
            "updated_at": now_ts,
        }

        product["categorias"] = categorias
        products[self.product_id] = product
        db.save_document("loja_products", products)

        panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, self.product_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class EditCategoryModal(disnake.ui.Modal):
    def __init__(self, product_id: str, category_id: str):
        self.product_id = product_id
        self.category_id = category_id

        # Carregar para preencher placeholders
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        cat = (product.get("categorias") or {}).get(category_id) or {}

        components = [
            disnake.ui.Label(
                text="Nome da categoria",
                component=disnake.ui.TextInput(
                    placeholder=cat.get("name") or "Ex.: Acessórios",
                    custom_id="category_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                ),
            ),
            disnake.ui.Label(
                text="Emoji (opcional)",
                component=disnake.ui.TextInput(
                    placeholder=cat.get("emoji") or "Ex.: 🔧 ou <:custom:123>",
                    custom_id="category_emoji",
                    style=disnake.TextInputStyle.short,
                    required=False,
                ),
            ),
            disnake.ui.Label(
                text="Pré-descrição (opcional)",
                component=disnake.ui.TextInput(
                    placeholder=cat.get("pre_description") or "Breve descrição para exibição nos menus",
                    custom_id="category_pre_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                ),
            ),
            disnake.ui.Label(
                text="Descrição (opcional)",
                component=disnake.ui.TextInput(
                    placeholder=cat.get("description") or "Descrição detalhada da categoria",
                    custom_id="category_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                ),
            ),
        ]

        super().__init__(title="Editar Categoria", components=components, custom_id=f"edit_category_modal:{product_id}:{category_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        valores = inter.resolved_values
        name = valores.get("category_name")
        emoji_str = validate_emoji_string(inter.bot, valores.get("category_emoji"))
        pre_desc = valores.get("category_pre_description")
        desc = valores.get("category_description")

        now_ts = int(disnake.utils.utcnow().timestamp())

        products = db.get_document("loja_products")
        product = products.get(self.product_id) or {}
        categorias = product.get("categorias") or {}
        cat = categorias.get(self.category_id)
        if not cat:
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, self.product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        cat["name"] = name
        cat["emoji"] = emoji_str
        cat["pre_description"] = pre_desc
        cat["description"] = desc
        cat["updated_at"] = now_ts
        categorias[self.category_id] = cat
        product["categorias"] = categorias
        products[self.product_id] = product
        db.save_document("loja_products", products)

        panel_data = ConfigurarCategoria.panel(inter, self.product_id, self.category_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class CategoryModals(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


def setup(bot: commands.Bot):
    bot.add_cog(CategoryModals(bot))


