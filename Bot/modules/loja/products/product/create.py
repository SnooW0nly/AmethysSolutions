import disnake
from urllib.parse import urlparse

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji
from functions.utils import utils

from .configurar import ConfigurarProduto

class CreateProductModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.Label(
                text="Nome do produto",
                component=disnake.ui.TextInput(
                    placeholder="Digite o nome do produto",
                    custom_id="product_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=100,
                ),
            ),
            disnake.ui.Label(
                text="Descrição do produto",
                component=disnake.ui.TextInput(
                    placeholder="Digite a descrição do produto",
                    custom_id="product_description",
                    style=disnake.TextInputStyle.paragraph,
                    required=False,
                    max_length=2000,
                ),
            ),
            disnake.ui.Label(
                text="Banner do produto",
                component=disnake.ui.TextInput(
                    placeholder="Digite a URL do banner do produto",
                    custom_id="product_banner",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=500,
                ),
            ),
            disnake.ui.Label(
                text="Cor da mensagem",
                component=disnake.ui.TextInput(
                    placeholder="Digite a cor da mensagem (HEX)",
                    custom_id="product_hex_color",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=7,
                ),
            ),
            disnake.ui.Label(
                text="Tipo de entrega",
                component=disnake.ui.StringSelect(
                    placeholder="Selecione o tipo de entrega do produto",
                    custom_id="product_delivery_type",
                    required=True,
                    options=[
                        disnake.SelectOption(label="Entrega Automática", description="O produto será entregue automaticamente após o pagamento.", value="automatic", emoji=emoji.reload),
                        disnake.SelectOption(label="Entrega Manual", description="O produto será entregue manualmente pelo suporte.", value="manual", emoji=emoji.hrench2),
                    ],
                ),
                description="Define se o produto será entregue automaticamente após o pagamento ou manualmente pelo suporte.",
            ),
        ]
        super().__init__(title="Criar Novo Produto", components=components, custom_id="create_product_modal")

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        valores = inter.resolved_values

        product_name = valores["product_name"]
        product_description = valores.get("product_description")
        product_id = utils.gerar_id()

        delivery_value = valores.get("product_delivery_type", "")
        if isinstance(delivery_value, (list, tuple)):
            product_delivery_type = delivery_value[0] if delivery_value else None
        else:
            product_delivery_type = delivery_value or None

        raw_banner = valores.get("product_banner")
        raw_hex = valores.get("product_hex_color")

        banner_value = raw_banner if utils.is_valid_url(raw_banner) else None
        hex_value = utils.normalize_hex_color(raw_hex)

        products = db.get_document("loja_products")
        products[product_id] = {
            "id": product_id,
            "name": product_name,
            "info": {
                "description": product_description,
                "banner": banner_value,
                "hex_color": hex_value,
                "delivery_type": product_delivery_type,
                # ── Novo: visível no site — desativado por padrão ──────────
                "visible": False,
                # ── Revenda — desativada por padrão ────────────────────────
                "resale": False,
                "created_at": int(disnake.utils.utcnow().timestamp()),
                "updated_at": int(disnake.utils.utcnow().timestamp()),
                "purchasesIds": [],
                "total_paid": 0,
                "display_preferences": {
                    "show_sales": True,
                    "show_options": True,
                    "show_stock": True,
                    "cart_duration_minutes": 30,
                    "store_hours": "",
                    "transcript_enabled": False
                },
                "buy_button": {
                    "label": "Comprar",
                    "emoji": emoji.cart
                }
            },
            "campos": {},
            "categorias": {},
            "messages": [],
            "cupons": {},
        }
        db.save_document("loja_products", products)

        panel_data = ConfigurarProduto.panel(inter, product_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)

class CreateProduct(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_CriarProduto":
            await inter.response.send_modal(CreateProductModal())

def setup(bot: commands.Bot):
    bot.add_cog(CreateProduct(bot))