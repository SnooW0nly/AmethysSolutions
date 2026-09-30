import disnake

from disnake.ext import commands
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db

from .configurar import ConfigurarCupom


class GerenciarCupons(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def gerar_dropdown_cupons(self, product: dict, product_id: str) -> disnake.ui.Select:
        cupons = product.get("cupons", {}) or {}
        options = []
        disabled = False

        for coupon in cupons.values():
            name = coupon.get("name") or coupon.get("id")
            uses_count = coupon.get("uses_count", 0)
            max_uses = coupon.get("max_uses")
            uses_str = f"{uses_count}"
            if max_uses:
                uses_str += f"/{max_uses}"
            desc = f"Usos: {uses_str} | Porcentagem: {coupon.get('percent', 0)}%"
            options.append(disnake.SelectOption(label=name, value=coupon.get("id"), description=desc))

        if not options:
            disabled = True
            options.append(disnake.SelectOption(label="Nenhum cupom encontrado", value="disabled"))

        return disnake.ui.StringSelect(
            placeholder=f"[{len(cupons)}] Selecione um cupom para gerenciar",
            options=options,
            custom_id=f"Loja_Cupons_Select:{product_id}",
            disabled=disabled,
        )

    def panel(self, inter: disnake.MessageInteraction, product_id: str):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return self._panel_embed(inter, product_id)
        return self._panel_components(inter, product_id)

    def _panel_components(self, inter: disnake.MessageInteraction, product_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        container_kwargs = {}
        if product.get('info', {}).get('hex_color'):
            container_kwargs["accent_colour"] = disnake.Colour(int(product['info']['hex_color'].replace("#", ""), 16))
        elif primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        dropdown = self.gerar_dropdown_cupons(product, product_id)

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Produto > **Cupons**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Selecione um cupom abaixo para gerenciá-lo.\nSe deseja criar um cupom, clique em **Criar Cupom**."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(dropdown),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Criar Cupom", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_CriarCupom:{product_id}"),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarProduto:{product_id}")),
        ]}

    def _panel_embed(self, inter: disnake.MessageInteraction, product_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        embed_kwargs = {}
        if product.get('info', {}).get('hex_color'):
            embed_kwargs["color"] = int(product['info']['hex_color'].replace("#", ""), 16)
        elif primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

        dropdown = self.gerar_dropdown_cupons(product, product_id)

        embed = disnake.Embed(
            description=f"-# Painel > Loja > Produto > **Cupons**\n\nSelecione um cupom para gerenciar. Para adicionar um novo, clique em **Criar Cupom**.",
            **embed_kwargs
        )

        components = [
            disnake.ui.ActionRow(dropdown),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Cupom", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_CriarCupom:{product_id}"),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarProduto:{product_id}")),
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id and custom_id.startswith("Loja_CuponsProduto"):
            # Abrir painel de cupons do produto
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
        if custom_id.startswith("Loja_Cupons_Select:"):
            product_id = custom_id.split(":", 1)[1]
            coupon_id = inter.values[0]
            if coupon_id == "disabled":
                return

            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                panel_data = ConfigurarCupom.panel(inter, product_id, coupon_id)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                panel_data = ConfigurarCupom.panel(inter, product_id, coupon_id)
                await inter.edit_original_message(**panel_data)


def setup(bot: commands.Bot):
    bot.add_cog(GerenciarCupons(bot))


