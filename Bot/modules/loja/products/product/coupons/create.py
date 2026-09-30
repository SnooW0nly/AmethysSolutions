import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji
from functions.utils import utils

from .cog import GerenciarCupons


class CreateCouponModal(disnake.ui.Modal):
    def __init__(self, product_id: str):
        self.product_id = product_id

        components = [
            disnake.ui.Label(
                text="Nome do cupom",
                component=disnake.ui.TextInput(
                    placeholder="Digite o nome do cupom",
                    custom_id="coupon_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=30,
                ),
            ),
            disnake.ui.Label(
                text="Porcentagem de desconto (0-100)",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: 15",
                    custom_id="coupon_percent",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=3,
                ),
            ),
            disnake.ui.Label(
                text="Dias de duração (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: 7",
                    custom_id="coupon_duration_days",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=4,
                ),
                description="Duração em dias a partir de agora. Deixe vazio para ilimitado.",
            ),
        ]
        super().__init__(title="Criar Cupom", components=components, custom_id=f"create_coupon_modal:{product_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        valores = inter.resolved_values
        name = valores.get("coupon_name")
        percent_str = valores.get("coupon_percent")
        duration_str = valores.get("coupon_duration_days")
        duration_days = None
        # Parse percent 0..100
        percent_value = 0
        try:
            if percent_str is not None:
                percent_value = int(float(str(percent_str).replace(",", ".")))
                if percent_value < 0:
                    percent_value = 0
                if percent_value > 100:
                    percent_value = 100
        except Exception:
            percent_value = 0
        try:
            if duration_str:
                duration_days = int(duration_str)
                if duration_days <= 0:
                    duration_days = None
        except Exception:
            duration_days = None

        now_ts = int(disnake.utils.utcnow().timestamp())
        expires_at = None
        if duration_days is not None:
            expires_at = now_ts + duration_days * 24 * 60 * 60

        products = db.get_document("loja_products")
        product = products.get(self.product_id) or {}
        cupons = product.get("cupons") or {}

        coupon_id = utils.gerar_id()
        cupons[coupon_id] = {
            "id": coupon_id,
            "name": name,
            "percent": percent_value,
            "active": True,
            "created_at": now_ts,
            "updated_at": now_ts,
            "expires_at": expires_at,
            "uses_count": 0,
            "max_uses": None,
            "min_cart": None,
            "max_cart": None,
            # Futuro: tipos de desconto, valores, etc.
        }
        product["cupons"] = cupons
        products[self.product_id] = product
        db.save_document("loja_products", products)

        panel_data = GerenciarCupons(self.bot).panel(inter, self.product_id) if hasattr(self, 'bot') else GerenciarCupons(inter.bot).panel(inter, self.product_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class CreateCoupon(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        if custom_id.startswith("Loja_CriarCupom:"):
            product_id = custom_id.split(":", 1)[1]
            modal = CreateCouponModal(product_id)
            modal.bot = self.bot
            await inter.response.send_modal(modal)


def setup(bot: commands.Bot):
    bot.add_cog(CreateCoupon(bot))


