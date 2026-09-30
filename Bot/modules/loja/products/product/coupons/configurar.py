import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from functions.text_utils import safe_textdisplay


def _coupon_status(c: dict) -> str:
    active = c.get("active", False)
    if not active:
        return "Inativo"
    now = int(disnake.utils.utcnow().timestamp())
    expires_at = c.get("expires_at")
    if expires_at and now >= int(expires_at):
        return "Expirado"
    max_uses = c.get("max_uses")
    uses = c.get("uses_count", 0)
    if isinstance(max_uses, int) and max_uses >= 0 and uses >= max_uses:
        return "Limite de usos atingido"
    return "Ativo"


class ConfigurarCupom(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str, coupon_id: str):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return ConfigurarCupom._panel_embed(inter, product_id, coupon_id)
        return ConfigurarCupom._panel_components(inter, product_id, coupon_id)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str, coupon_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        coupon = (product.get("cupons") or {}).get(coupon_id) or {}

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        container_kwargs = {}
        if product.get('info', {}).get('hex_color'):
            container_kwargs["accent_colour"] = disnake.Colour(int(product['info']['hex_color'].replace("#", ""), 16))
        elif primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        status_str = _coupon_status(coupon)
        button_ativo = disnake.ui.Button(label="Ativo" if coupon.get("active") else "Inativo", emoji=emoji.on if coupon.get("active") else emoji.off, custom_id=f"Loja_ToggleCupom:{product_id}:{coupon_id}")

        coupon_name = safe_textdisplay(coupon.get('name', coupon_id), 50)
        header_text = safe_textdisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Produto > Cupom > **{coupon_name}**")
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(header_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Informações do cupom**"),
                disnake.ui.Section(
                disnake.ui.TextDisplay(safe_textdisplay(f"""-# Nome: `{coupon.get('name', '-')[:50]}` | Status: `{status_str}`
-# Desconto: `{coupon.get('percent', 0)}%` | Usos: `{coupon.get('uses_count', 0)}`{f"/`{coupon.get('max_uses')}`" if coupon.get('max_uses') is not None else ''}
-# Mín. carrinho: `{utils.format_price_brl(coupon.get('min_cart')) if coupon.get('min_cart') is not None else 'Nenhum'}` | Máx. carrinho: `{utils.format_price_brl(coupon.get('max_cart')) if coupon.get('max_cart') is not None else 'Nenhum'}`""")),
                    accessory=button_ativo
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"""
-# Criado em: {utils.format_timestamp(coupon.get('created_at'))}
-# Última edição: {utils.format_timestamp(coupon.get('updated_at'))}
-# Expira em: {utils.format_timestamp(coupon['expires_at']) if coupon.get('expires_at') else 'Ilimitado'}
                """),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Editar informações", emoji=emoji.edit, custom_id=f"Loja_EditarCupom:{product_id}:{coupon_id}"),
                    disnake.ui.Button(label="Avançados", emoji=emoji.settings2, custom_id=f"Loja_AvancadoCupom:{product_id}:{coupon_id}"),
                    disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Loja_ApagarCupom:{product_id}:{coupon_id}"),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_CuponsProduto:{product_id}")),
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str, coupon_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        coupon = (product.get("cupons") or {}).get(coupon_id) or {}

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        embed_kwargs = {}
        if product.get('info', {}).get('hex_color'):
            embed_kwargs["color"] = int(product['info']['hex_color'].replace("#", ""), 16)
        elif primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

        status_str = _coupon_status(coupon)

        embed_description = (
            f"-# Painel > Loja > Produto > Cupom > **{coupon.get('name', coupon_id)}**\n\n"
            f"**Informações do cupom**\n"
            f"-# Nome: `{coupon.get('name', '-')}`\n"
            f"-# Status: `{status_str}`\n"
            f"-# Desconto: `{coupon.get('percent', 0)}%`\n"
            f"-# Criado em: {utils.format_timestamp(coupon.get('created_at'))}\n"
            f"-# Última edição: {utils.format_timestamp(coupon.get('updated_at'))}\n"
            f"-# Expira em: `{utils.format_timestamp(coupon['expires_at']) if coupon.get('expires_at') else 'Ilimitado'}`\n"
            f"-# Usos: `{coupon.get('uses_count', 0)}`{f"/`{coupon.get('max_uses')}`" if coupon.get('max_uses') is not None else ''}\n"
            f"-# Mín. carrinho: `{utils.format_price_brl(coupon.get('min_cart')) if coupon.get('min_cart') is not None else 'Nenhum'}` | Máx. carrinho: `{utils.format_price_brl(coupon.get('max_cart')) if coupon.get('max_cart') is not None else 'Nenhum'}`\n"
        )

        embed = disnake.Embed(description=embed_description, **embed_kwargs)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar", emoji=emoji.edit, custom_id=f"Loja_EditarCupom:{product_id}:{coupon_id}"),
                disnake.ui.Button(label="Avançado", emoji=emoji.commands, custom_id=f"Loja_AvancadoCupom:{product_id}:{coupon_id}"),
                disnake.ui.Button(label="Alternar ativo", emoji=emoji.reload, custom_id=f"Loja_ToggleCupom:{product_id}:{coupon_id}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Loja_ApagarCupom:{product_id}:{coupon_id}"),
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_CuponsProduto:{product_id}"),
            ),
        ]
        return {"embed": embed, "components": components}


def setup(bot: commands.Bot):
    bot.add_cog(ConfigurarCupom(bot))


