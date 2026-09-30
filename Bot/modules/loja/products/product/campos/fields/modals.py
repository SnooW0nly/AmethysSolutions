import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from functions.utils import utils
from functions.loja_products import parse_price_brl_to_float, validate_emoji_string
from ..cog import GerenciarCamposCategorias
from .configurar import ConfigurarCampo

def _parse_price(value: str) -> float:
    return parse_price_brl_to_float(value)


class CreateFieldModal(disnake.ui.Modal):
    def __init__(self, product_id: str, category_id: str | None = None):
        self.product_id = product_id
        self.category_id = category_id

        components = [
            disnake.ui.Label(
                text="Nome do campo",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: VIP 30d, Plano, Produto, etc.",
                    custom_id="field_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=100,

                ),
            ),
            disnake.ui.Label(
                text="Preço (BRL)",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: 19,90",
                    custom_id="field_price",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=10,
                ),
            ),
            disnake.ui.Label(
                text="Emoji (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: 🛒 ou <:custom:123>",
                    custom_id="field_emoji",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=100,
                ),
            ),
            disnake.ui.Label(
                text="Pré-descrição (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Breve texto para exibição nas listas",
                    custom_id="field_pre_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=500,
                ),
            ),
            disnake.ui.Label(
                text="Descrição (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Descrição detalhada do campo",
                    custom_id="field_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=500,
                ),
            ),
        ]

        super().__init__(title="Criar Campo", components=components, custom_id=f"create_field_modal:{product_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        valores = inter.resolved_values

        name = valores.get("field_name")
        price = _parse_price(valores.get("field_price"))
        emoji_str = validate_emoji_string(inter.bot, valores.get("field_emoji"))
        pre_desc = valores.get("field_pre_description")
        desc = valores.get("field_description")
        instructions = None  # Instruções devem ser adicionadas via EditInstructionsModal

        now_ts = int(disnake.utils.utcnow().timestamp())

        products = db.get_document("loja_products")
        product = products.get(self.product_id) or {}
        campos = product.get("campos") or {}

        field_id = utils.gerar_id()
        campos[field_id] = {
            "id": field_id,
            "name": name,
            "price": price,
            "emoji": emoji_str,
            "pre_description": pre_desc,
            "description": desc,
            "instructions": instructions,
            "category_id": self.category_id,
            "created_at": now_ts,
            "updated_at": now_ts,
            "advanced": {},
            "stock": [],
            "cargos": {"adicionar": [], "remover": []},
            "condicoes": {"valorMin": None, "valorMax": None, "quantidadeMin": None, "quantidadeMax": None},
        }
        product["campos"] = campos
        products[self.product_id] = product
        db.save_document("loja_products", products)
        
        # Sincronizar silenciosamente todas as mensagens do produto
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(inter.client, self.product_id)

        panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, self.product_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class EditFieldModal(disnake.ui.Modal):
    def __init__(self, product_id: str, field_id: str):
        self.product_id = product_id
        self.field_id = field_id

        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id) or {}

        price_placeholder = utils.format_price_brl(float(field.get("price") or 0.0))

        components = [
            disnake.ui.Label(
                text="Nome do campo",
                component=disnake.ui.TextInput(
                    custom_id="field_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=100,
                    value=field.get("name") or "",
                ),
            ),
            disnake.ui.Label(
                text="Preço (BRL)",
                component=disnake.ui.TextInput(
                    custom_id="field_price",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    value=price_placeholder,
                    max_length=10
                ),
            ),
            disnake.ui.Label(
                text="Emoji (opcional)",
                component=disnake.ui.TextInput(
                    custom_id="field_emoji",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=100,
                    value=field.get("emoji") or "",
                ),
            ),
            disnake.ui.Label(
                text="Pré-descrição (opcional)",
                component=disnake.ui.TextInput(
                    custom_id="field_pre_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=500,
                    value=field.get("pre_description") or "",
                ),
            ),
            disnake.ui.Label(
                text="Descrição (opcional)",
                component=disnake.ui.TextInput(
                    custom_id="field_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=500,
                    value=field.get("description") or "",
                ),
            ),
        ]

        super().__init__(title="Editar Campo", components=components, custom_id=f"edit_field_modal:{product_id}:{field_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        valores = inter.resolved_values
        name = valores.get("field_name")
        price = _parse_price(valores.get("field_price"))
        emoji_str = validate_emoji_string(inter.bot, valores.get("field_emoji"))
        pre_desc = valores.get("field_pre_description")
        desc = valores.get("field_description")

        now_ts = int(disnake.utils.utcnow().timestamp())

        products = db.get_document("loja_products")
        product = products.get(self.product_id) or {}
        campos = product.get("campos") or {}
        field = campos.get(self.field_id)
        if not field:
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, self.product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        field["name"] = name
        field["price"] = price
        field["emoji"] = emoji_str
        field["pre_description"] = pre_desc
        field["description"] = desc
        campos[self.field_id] = field
        product["campos"] = campos
        products[self.product_id] = product
        db.save_document("loja_products", products)
        
        # Sincronizar silenciosamente todas as mensagens do produto
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(inter.client, self.product_id)

        panel_data = ConfigurarCampo.panel(inter, self.product_id, self.field_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class EditInstructionsModal(disnake.ui.Modal):
    """Modal para editar apenas as instruções do campo"""
    
    def __init__(self, product_id: str, field_id: str):
        self.product_id = product_id
        self.field_id = field_id
        
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id) or {}
        
        components = [
            disnake.ui.Label(
                text="Instruções (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Instruções que serão enviadas ao usuário após a compra",
                    custom_id="field_instructions",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=2000,
                    value=field.get("instructions") or "",
                ),
            ),
        ]
        
        super().__init__(title="Editar Instruções", components=components, custom_id=f"edit_instructions_modal:{product_id}:{field_id}")
    
    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        
        valores = inter.resolved_values
        instructions = valores.get("field_instructions")
        
        products = db.get_document("loja_products")
        product = products.get(self.product_id) or {}
        campos = product.get("campos") or {}
        field = campos.get(self.field_id)
        
        if not field:
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, self.product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return
        
        field["instructions"] = instructions
        field["updated_at"] = int(disnake.utils.utcnow().timestamp())
        campos[self.field_id] = field
        product["campos"] = campos
        products[self.product_id] = product
        db.save_document("loja_products", products)
        
        # Sincronizar silenciosamente todas as mensagens do produto
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(inter.client, self.product_id)
        
        panel_data = ConfigurarCampo.panel(inter, self.product_id, self.field_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class FieldModals(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


def setup(bot: commands.Bot):
    bot.add_cog(FieldModals(bot))


