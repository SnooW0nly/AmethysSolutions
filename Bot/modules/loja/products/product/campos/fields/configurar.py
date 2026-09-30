import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from functions.text_utils import safe_textdisplay
# Import moved inside methods to avoid circular import with ..cog
from functions.loja_products import get_stock_quantity
from modules.loja.cart.stock_manager import StockManager

def _get_stock_display(product_id: str, field_id: str) -> str:
    """Retorna a quantidade de estoque formatada (Infinito ou número)"""
    products = db.get_document("loja_products") or {}
    product = products.get(product_id, {})
    campo = product.get("campos", {}).get(field_id, {})
    
    # Verificar se é estoque infinito
    if campo.get("infinite_stock", {}).get("enabled"):
        return "Infinito"
    
    # Obter estoque do sistema centralizado
    stock_qtd = StockManager.get_available_stock(product_id, field_id)
    return str(stock_qtd)


class ConfigurarCampo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str, field_id: str):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return ConfigurarCampo._panel_embed(inter, product_id, field_id)
        return ConfigurarCampo._panel_components(inter, product_id, field_id)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id)
        if not field:
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

        stock_qtd = _get_stock_display(product_id=product_id, field_id=field_id)

        pre_desc = field.get("pre_description")
        if pre_desc:
            # Truncar se muito grande
            if len(pre_desc) > 500:
                pre_desc = pre_desc[:500] + "..."
            wrapped_pre = utils.wrap_text_hyphenate(pre_desc, 40)
            if len(wrapped_pre) > 1500:
                wrapped_pre = wrapped_pre[:1500] + "..."
            pre_desc_block = f"\n```{wrapped_pre}```"
        else:
            pre_desc_block = "`Não configurada`"
            
        desc_value = field.get("description")
        if desc_value:
            # Truncar se muito grande
            if len(desc_value) > 500:
                desc_value = desc_value[:500] + "..."
            wrapped_desc = utils.wrap_text_hyphenate(desc_value, 40)
            if len(wrapped_desc) > 1500:
                wrapped_desc = wrapped_desc[:1500] + "..."
            desc_block = f"\n```{wrapped_desc}```"
        else:
            desc_block = "`Não configurada`"
        
        instructions_value = field.get("instructions")
        if instructions_value:
            # Truncar se muito grande
            if len(instructions_value) > 500:
                instructions_value = instructions_value[:500] + "..."
            wrapped_instructions = utils.wrap_text_hyphenate(instructions_value, 40)
            if len(wrapped_instructions) > 1500:
                wrapped_instructions = wrapped_instructions[:1500] + "..."
            instructions_block = f"\n```{wrapped_instructions}```"
        else:
            instructions_block = "`Não configurada`"
        
        emoji_value = field.get("emoji")
        emoji_display = emoji_value if emoji_value else "`Não configurado`"

        price = float(field.get("price") or 0.0)
        is_subscription = field.get("is_subscription", False)
        cond = field.get("condicoes") or {}
        vmin = cond.get("valorMin")
        vmax = cond.get("valorMax")
        qmin = cond.get("quantidadeMin")
        qmax = cond.get("quantidadeMax")

        product_name = safe_textdisplay(product.get("name") or product_id, 50)
        field_name = safe_textdisplay(field.get('name', field_id), 50)
        
        header_text = safe_textdisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > {product_name} > Campo > **{field_name}**")
        
        mode_text = "Assinatura" if is_subscription else "Produto"
        stock_info = f"Estoque: `{stock_qtd}`" if not is_subscription else "Estoque: `Desativado`"
        
        info_text = safe_textdisplay(f"""-# Nome: `{field.get('name', '-')[:50]}` | Emoji: {emoji_display}
-# Preço: `{utils.format_price_brl(price)}` | Modo: `{mode_text}`
-# {stock_info}
-# Pré-descrição: {pre_desc_block}
-# Descrição: {desc_block}
-# Instruções: {instructions_block}""")
        
        management_text = safe_textdisplay(f"""-# Criado em: {utils.format_timestamp(field.get('created_at'))}
-# Última edição: {utils.format_timestamp(field.get('updated_at'))}""")
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(header_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Informações do campo**"),
                disnake.ui.TextDisplay(info_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Gerenciamento do campo**"),
                disnake.ui.TextDisplay(management_text),
                disnake.ui.TextDisplay("**Condições atuais**"),
                disnake.ui.TextDisplay(
                    f"-# Valor mínimo: `{vmin if vmin is not None else '-'}" + "`\n"
                    f"-# Valor máximo: `{vmax if vmax is not None else '-'}" + "`\n"
                    f"-# Quantidade mínima: `{qmin if qmin is not None else '-'}" + "`\n"
                    f"-# Quantidade máxima: `{qmax if qmax is not None else '-'}" + "`\n"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Editar", emoji=emoji.edit, custom_id=f"Loja_EditarCampo:{product_id}:{field_id}"),
                    disnake.ui.Button(label="Cargos", emoji=emoji.role, custom_id=f"Loja_CargosCampo:{product_id}:{field_id}"),
                    disnake.ui.Button(label="Condições", emoji=emoji.settings2, custom_id=f"Loja_CondicoesCampo:{product_id}:{field_id}"),
                ),
                disnake.ui.ActionRow(
                    *([disnake.ui.Button(
                        label="Ativar Campo" if field.get("boost_disabled") else "Desativar Campo",
                        emoji=emoji.power if field.get("boost_disabled") else f"{emoji.power}",
                        style=disnake.ButtonStyle.green if field.get("boost_disabled") else disnake.ButtonStyle.grey,
                        custom_id=f"Loja_ToggleBoostCampo:{product_id}:{field_id}",
                    )] if field.get("boost_field") else [
                        disnake.ui.Button(
                            label="Tornar Produto" if is_subscription else "Tornar Assinatura",
                            emoji=emoji.cart if is_subscription else emoji.calendar,
                            style=disnake.ButtonStyle.blurple,
                            custom_id=f"Loja_ToggleSubscription:{product_id}:{field_id}"
                        ),
                        *( [disnake.ui.Button(label="Integração", emoji=emoji.link, custom_id=f"Loja_IntegracaoVIP:{product_id}:{field_id}")] if is_subscription else [disnake.ui.Button(label="Estoque", emoji=emoji.cardbox, custom_id=f"Loja_EstoqueCampo:{product_id}:{field_id}")] )
                    ]),
                    *([
                        disnake.ui.Button(label="Instruções", emoji=emoji.information, custom_id=f"Loja_InstrucoesCampo:{product_id}:{field_id}"),
                        disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Loja_ApagarCampo:{product_id}:{field_id}"),
                    ]),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_CamposProduto:{product_id}")),
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str, field_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id)
        if not field:
            from ..cog import GerenciarCamposCategorias
            return GerenciarCamposCategorias(inter.bot)._panel_embed(inter, product_id)

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        embed_kwargs = {}
        if product.get('info', {}).get('hex_color'):
            embed_kwargs["color"] = int(product['info']['hex_color'].replace("#", ""), 16)
        elif primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

        stock_qtd = _get_stock_display(product_id=product_id, field_id=field_id)
        price = float(field.get("price") or 0.0)
        is_subscription = field.get("is_subscription", False)

        pre_desc = field.get("pre_description")
        pre_desc_block = f"\n```{utils.wrap_text_hyphenate(pre_desc, 40)}```" if pre_desc else "`Não configurada`"
        desc_value = field.get("description")
        desc_block = f"\n```{utils.wrap_text_hyphenate(desc_value, 40)}```" if desc_value else "`Não configurada`"
        instructions_value = field.get("instructions")
        instructions_block = f"\n```{utils.wrap_text_hyphenate(instructions_value, 40)}```" if instructions_value else "`Não configurada`"
        emoji_value = field.get("emoji")
        emoji_display = emoji_value if emoji_value else "`Não configurado`"

        product_name = product.get("name") or product_id
        cond = field.get("condicoes") or {}
        vmin = cond.get("valorMin")
        vmax = cond.get("valorMax")
        qmin = cond.get("quantidadeMin")
        qmax = cond.get("quantidadeMax")

        mode_text = "Assinatura" if is_subscription else "Produto"
        stock_info = f"Estoque: `{stock_qtd}`" if not is_subscription else "Estoque: `Desativado`"
        
        embed_description = (
            f"-# Painel > Loja > {product_name} > **Campo > {field.get('name', field_id)}**\n\n"
            f"**Informações do campo**\n"
            f"-# Nome: `{field.get('name', '-')}` | Emoji: {emoji_display}\n"
            f"-# Preço: `{utils.format_price_brl(price)}` | Modo: `{mode_text}`\n"
            f"-# {stock_info}\n"
            f"-# Pré-descrição: {pre_desc_block}\n"
            f"-# Descrição: {desc_block}\n"
            f"-# Instruções: {instructions_block}\n\n"
            f"**Gerenciamento**\n"
            f"-# Criado em: {utils.format_timestamp(field.get('created_at'))}\n"
            f"-# Última edição: {utils.format_timestamp(field.get('updated_at'))}\n\n"
            f"**Condições atuais**\n"
            f"-# Valor mínimo: `{vmin if vmin is not None else '-'}" + "`\n"
            f"-# Valor máximo: `{vmax if vmax is not None else '-'}" + "`\n"
            f"-# Quantidade mínima: `{qmin if qmin is not None else '-'}" + "`\n"
            f"-# Quantidade máxima: `{qmax if qmax is not None else '-'}" + "`"
        )

        embed = disnake.Embed(description=embed_description, **embed_kwargs)
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar", emoji=emoji.edit, custom_id=f"Loja_EditarCampo:{product_id}:{field_id}"),
                disnake.ui.Button(label="Cargos", emoji=emoji.role, custom_id=f"Loja_CargosCampo:{product_id}:{field_id}"),
                disnake.ui.Button(label="Condições", emoji=emoji.settings2, custom_id=f"Loja_CondicoesCampo:{product_id}:{field_id}"),
            ),
            disnake.ui.ActionRow(
                *([disnake.ui.Button(
                    label="Ativar Campo" if field.get("boost_disabled") else "Desativar Campo",
                    emoji="✅" if field.get("boost_disabled") else "🔴",
                    style=disnake.ButtonStyle.green if field.get("boost_disabled") else disnake.ButtonStyle.grey,
                    custom_id=f"Loja_ToggleBoostCampo:{product_id}:{field_id}",
                )] if field.get("boost_field") else [
                    disnake.ui.Button(
                        label="Tornar Produto" if is_subscription else "Tornar Assinatura",
                        emoji=emoji.cart if is_subscription else emoji.calendar,
                        style=disnake.ButtonStyle.blurple,
                        custom_id=f"Loja_ToggleSubscription:{product_id}:{field_id}"
                    ),
                    *( [disnake.ui.Button(label="Integração", emoji=emoji.link, custom_id=f"Loja_IntegracaoVIP:{product_id}:{field_id}")] if is_subscription else [disnake.ui.Button(label="Estoque", emoji=emoji.cardbox, custom_id=f"Loja_EstoqueCampo:{product_id}:{field_id}")] )
                ]),
                disnake.ui.Button(label="Instruções", emoji=emoji.information, custom_id=f"Loja_InstrucoesCampo:{product_id}:{field_id}"),
                disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Loja_ApagarCampo:{product_id}:{field_id}"),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_CamposProduto:{product_id}")),
        ]
        return {"embed": embed, "components": components}



def setup(bot: commands.Bot):
    bot.add_cog(ConfigurarCampo(bot))


# ─────────────────────────────────────────────────────────────────────────────
#  Boost field helpers
# ─────────────────────────────────────────────────────────────────────────────

# Variantes de campos boost gerados automaticamente:
# (nome, boosts, periodicidade)
BOOST_FIELD_VARIANTS = [
    ("2x Impulso Mensal",    2,  "mensal"),
    ("4x Impulso Mensal",    4,  "mensal"),
    ("6x Impulso Mensal",    6,  "mensal"),
    ("8x Impulso Mensal",    8,  "mensal"),
    ("12x Impulso Mensal",   12, "mensal"),
    ("14x Impulso Mensal",   14, "mensal"),
    ("2x Impulso Trimestral",  2,  "trimestral"),
    ("4x Impulso Trimestral",  4,  "trimestral"),
    ("6x Impulso Trimestral",  6,  "trimestral"),
    ("8x Impulso Trimestral",  8,  "trimestral"),
    ("12x Impulso Trimestral", 12, "trimestral"),
    ("14x Impulso Trimestral", 14, "trimestral"),
]
