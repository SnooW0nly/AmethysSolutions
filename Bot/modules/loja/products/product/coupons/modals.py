import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from functions.utils import utils

from .configurar import ConfigurarCupom


class EditCouponModal(disnake.ui.Modal):
    def __init__(self, product_id: str, coupon_id: str):
        self.product_id = product_id
        self.coupon_id = coupon_id

        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        coupon = (product.get("cupons") or {}).get(coupon_id) or {}

        components = [
            disnake.ui.Label(
                text="Nome do cupom",
                component=disnake.ui.TextInput(
                    placeholder="Digite o nome do cupom",
                    custom_id="coupon_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=30,
                    value=coupon.get("name", ""),
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
                    value=str(coupon.get("percent", 0)),
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
                    value="" if not coupon.get("expires_at") else str(max(1, int((int(coupon['expires_at']) - int(disnake.utils.utcnow().timestamp())) / 86400))),
                ),
            ),
        ]
        super().__init__(title="Editar Cupom", components=components, custom_id=f"edit_coupon_modal:{product_id}:{coupon_id}")

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

        products = db.get_document("loja_products")
        product = products.get(self.product_id) or {}
        coupon = (product.get("cupons") or {}).get(self.coupon_id) or {}

        now_ts = int(disnake.utils.utcnow().timestamp())
        # Clamp percent 0..100
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

        coupon["name"] = name
        coupon["percent"] = percent_value
        coupon["updated_at"] = now_ts

        if duration_str:
            try:
                duration_days = int(duration_str)
                if duration_days > 0:
                    coupon["expires_at"] = now_ts + duration_days * 86400
            except Exception:
                pass
        elif duration_str == "":
            coupon["expires_at"] = None

        product.setdefault("cupons", {})[self.coupon_id] = coupon
        products[self.product_id] = product
        db.save_document("loja_products", products)

        panel_data = ConfigurarCupom.panel(inter, self.product_id, self.coupon_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class AdvancedCouponModal(disnake.ui.Modal):
    def __init__(self, product_id: str, coupon_id: str):
        self.product_id = product_id
        self.coupon_id = coupon_id

        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        coupon = (product.get("cupons") or {}).get(coupon_id) or {}

        components = [
            disnake.ui.Label(
                text="Máximo de usos (opcional)",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: 100",
                    custom_id="coupon_max_uses",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=10,
                    value="" if coupon.get("max_uses") is None else str(coupon.get("max_uses")),
                ),
            ),
            disnake.ui.Label(
                text="Mínimo no carrinho (opcional)",
                description="Valor em BRL. Use ponto ou vírgula.",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: 10,00",
                    custom_id="coupon_min_cart",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=15,
                    value="" if coupon.get("min_cart") is None else str(coupon.get("min_cart")),
                ),
            ),
            disnake.ui.Label(
                text="Máximo no carrinho (opcional)",
                description="Valor em BRL. Use ponto ou vírgula.",
                component=disnake.ui.TextInput(
                    placeholder="Ex.: 250,00",
                    custom_id="coupon_max_cart",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=15,
                    value="" if coupon.get("max_cart") is None else str(coupon.get("max_cart")),
                ),
            ),
        ]
        super().__init__(title="Avançado - Cupom", components=components, custom_id=f"advanced_coupon_modal:{product_id}:{coupon_id}")

    @staticmethod
    def _parse_money(value: str):
        if value is None:
            return None
        s = str(value).strip().replace("R$", "").replace(" ", "").replace(",", ".")
        if s == "":
            return None
        try:
            return float(s)
        except Exception:
            return None

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)

        valores = inter.resolved_values
        max_uses_raw = valores.get("coupon_max_uses")
        min_cart_raw = valores.get("coupon_min_cart")
        max_cart_raw = valores.get("coupon_max_cart")

        products = db.get_document("loja_products")
        product = products.get(self.product_id) or {}
        coupon = (product.get("cupons") or {}).get(self.coupon_id) or {}

        now_ts = int(disnake.utils.utcnow().timestamp())
        coupon["updated_at"] = now_ts

        try:
            coupon["max_uses"] = int(max_uses_raw) if max_uses_raw not in (None, "") else None
        except Exception:
            coupon["max_uses"] = None
        coupon["min_cart"] = self._parse_money(min_cart_raw)
        coupon["max_cart"] = self._parse_money(max_cart_raw)

        product.setdefault("cupons", {})[self.coupon_id] = coupon
        products[self.product_id] = product
        db.save_document("loja_products", products)

        panel_data = ConfigurarCupom.panel(inter, self.product_id, self.coupon_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


