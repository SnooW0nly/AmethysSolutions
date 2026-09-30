import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils

# Import moved inside methods to avoid circular import with ..cog

class ConfigurarCategoria(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str, category_id: str):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return ConfigurarCategoria._panel_embed(inter, product_id, category_id)
        return ConfigurarCategoria._panel_components(inter, product_id, category_id)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str, category_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        categoria = (product.get("categorias") or {}).get(category_id)
        if not categoria:
            mode = db.get_document("custom_mode").get("mode")
            from ..cog import GerenciarCamposCategorias
            panel_data = GerenciarCamposCategorias(inter.bot).panel(inter, product_id)
            if mode == "embed":
                return {"embed": panel_data.get("embed"), "components": panel_data.get("components")}
            return panel_data

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        container_kwargs = {}
        if product.get('info', {}).get('hex_color'):
            container_kwargs["accent_colour"] = disnake.Colour(int(product['info']['hex_color'].replace("#", ""), 16))
        elif primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        # Estatísticas e lista de campos dentro da categoria
        campos = product.get("campos", {}) or {}
        campos_na_categoria = sum(1 for c in campos.values() if c.get("category_id") == category_id)
        options = []
        disabled = False
        for campo in campos.values():
            if campo.get("category_id") != category_id:
                continue
            name = campo.get("name") or campo.get("id")
            options.append(disnake.SelectOption(label=name, value=campo.get("id"), description="Campo da categoria"))
        if not options:
            disabled = True
            options.append(disnake.SelectOption(label="Nenhum campo nesta categoria", value="disabled"))
        dropdown_campos_categoria = disnake.ui.StringSelect(
            placeholder=f"[{campos_na_categoria}] Selecione um campo desta categoria",
            options=options,
            custom_id=f"Loja_CamposCategoria_Select:{product_id}:{category_id}",
            disabled=disabled,
        )

        pre_desc = categoria.get("pre_description")
        pre_desc_block = f"\n```{utils.wrap_text_hyphenate(pre_desc, 40)}```" if pre_desc else "`Não configurada`"
        desc = categoria.get("description")
        desc_block = f"\n```{utils.wrap_text_hyphenate(desc, 40)}```" if desc else "`Não configurada`"
        emoji_value = categoria.get("emoji")
        emoji_display = emoji_value if emoji_value else "`Não configurado`"

        product_name = product.get("name") or product_id
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > {product_name} > **Categoria > {categoria.get('name', category_id)}**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Informações da categoria**"),
                disnake.ui.TextDisplay(f"""
-# Nome: `{categoria.get('name', '-')}` | Emoji: {emoji_display}
-# Pré-descrição: {pre_desc_block}
-# Descrição: {desc_block}
                """),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Gerenciamento da categoria**"),
                disnake.ui.TextDisplay(f"""
-# Criado em: {utils.format_timestamp(categoria.get('created_at'))}
-# Última edição: {utils.format_timestamp(categoria.get('updated_at'))}
-# Campos nesta categoria: `{campos_na_categoria}`
                """),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Campos nesta categoria**"),
                disnake.ui.ActionRow(dropdown_campos_categoria),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Criar Campo", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_CriarCampoCategoria:{product_id}:{category_id}"),
                    disnake.ui.Button(label="Editar", emoji=emoji.edit, custom_id=f"Loja_EditarCategoria:{product_id}:{category_id}"),
                    disnake.ui.Button(label="Campos da Categoria", emoji=emoji.cardbox, custom_id=f"Loja_CamposCategoria:{product_id}:{category_id}"),
                    disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Loja_ApagarCategoria:{product_id}:{category_id}"),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_CamposProduto_Voltar:{product_id}")),
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str, category_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        categoria = (product.get("categorias") or {}).get(category_id)
        if not categoria:
            from ..cog import GerenciarCamposCategorias
            return GerenciarCamposCategorias(inter.bot)._panel_embed(inter, product_id)

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        embed_kwargs = {}
        if product.get('info', {}).get('hex_color'):
            embed_kwargs["color"] = int(product['info']['hex_color'].replace("#", ""), 16)
        elif primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

        campos = product.get("campos", {}) or {}
        campos_na_categoria = sum(1 for c in campos.values() if c.get("category_id") == category_id)
        pre_desc = categoria.get("pre_description")
        pre_desc_block = f"\n```{utils.wrap_text_hyphenate(pre_desc, 40)}```" if pre_desc else "`Não configurada`"
        desc = categoria.get("description")
        desc_block = f"\n```{utils.wrap_text_hyphenate(desc, 40)}```" if desc else "`Não configurada`"
        emoji_value = categoria.get("emoji")
        emoji_display = emoji_value if emoji_value else "`Não configurado`"

        product_name = product.get("name") or product_id
        embed_description = (
            f"-# Painel > Loja > {product_name} > **Categoria > {categoria.get('name', category_id)}**\n\n"
            f"**Informações da categoria**\n"
            f"-# Nome: `{categoria.get('name', '-')}` | Emoji: {emoji_display}\n"
            f"-# Pré-descrição: {pre_desc_block}\n"
            f"-# Descrição: {desc_block}\n\n"
            f"**Gerenciamento**\n"
            f"-# Criado em: {utils.format_timestamp(categoria.get('created_at'))}\n"
            f"-# Última edição: {utils.format_timestamp(categoria.get('updated_at'))}\n"
            f"-# Campos nesta categoria: `{campos_na_categoria}`"
        )

        embed = disnake.Embed(description=embed_description, **embed_kwargs)
        # Rebuild dropdown for embed section as well
        options = []
        disabled = False
        for campo in campos.values():
            if campo.get("category_id") != category_id:
                continue
            name = campo.get("name") or campo.get("id")
            options.append(disnake.SelectOption(label=name, value=campo.get("id"), description="Campo da categoria"))
        if not options:
            disabled = True
            options.append(disnake.SelectOption(label="Nenhum campo nesta categoria", value="disabled"))
        dropdown_campos_categoria = disnake.ui.StringSelect(
            placeholder=f"[{campos_na_categoria}] Selecione um campo desta categoria",
            options=options,
            custom_id=f"Loja_CamposCategoria_Select:{product_id}:{category_id}",
            disabled=disabled,
        )

        components = [
            disnake.ui.ActionRow(dropdown_campos_categoria),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Campo", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"Loja_CriarCampoCategoria:{product_id}:{category_id}"),
                disnake.ui.Button(label="Editar", emoji=emoji.edit, custom_id=f"Loja_EditarCategoria:{product_id}:{category_id}"),
                disnake.ui.Button(label="Campos da Categoria", emoji=emoji.cardbox, custom_id=f"Loja_CamposCategoria:{product_id}:{category_id}"),
                disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Loja_ApagarCategoria:{product_id}:{category_id}"),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_CamposProduto_Voltar:{product_id}")),
        ]
        return {"embed": embed, "components": components}


def setup(bot: commands.Bot):
    bot.add_cog(ConfigurarCategoria(bot))


