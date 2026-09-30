import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message

from .modals import EditCouponModal, AdvancedCouponModal
from .configurar import ConfigurarCupom
from .cog import GerenciarCupons


class CouponActions(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""

        if custom_id.startswith("Loja_EditarCupom:"):
            _, product_id, coupon_id = custom_id.split(":", 2)
            await inter.response.send_modal(EditCouponModal(product_id, coupon_id))

        elif custom_id.startswith("Loja_AvancadoCupom:"):
            _, product_id, coupon_id = custom_id.split(":", 2)
            await inter.response.send_modal(AdvancedCouponModal(product_id, coupon_id))

        elif custom_id.startswith("Loja_ToggleCupom:"):
            _, product_id, coupon_id = custom_id.split(":", 2)
            products = db.get_document("loja_products")
            product = products.get(product_id) or {}
            coupon = (product.get("cupons") or {}).get(coupon_id) or {}

            coupon["active"] = not bool(coupon.get("active", True))
            db.save_document("loja_products", products)

            mode = db.get_document("custom_mode").get("mode")
            panel_data = ConfigurarCupom.panel(inter, product_id, coupon_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)

        elif custom_id.startswith("Loja_ApagarCupom:"):
            _, product_id, coupon_id = custom_id.split(":", 2)
            products = db.get_document("loja_products")
            product = products.get(product_id) or {}
            cupons = product.get("cupons") or {}
            if coupon_id in cupons:
                del cupons[coupon_id]
                product["cupons"] = cupons
                products[product_id] = product
                db.save_document("loja_products", products)

            mode = db.get_document("custom_mode").get("mode")
            panel_data = GerenciarCupons(self.bot).panel(inter, product_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)


def setup(bot: commands.Bot):
    bot.add_cog(CouponActions(bot))


