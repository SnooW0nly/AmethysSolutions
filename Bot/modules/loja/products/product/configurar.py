from disnake.ext import commands
import disnake

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from functions.utils import utils
from functions.text_utils import wrap_text

class _ResaleCommissionModal(disnake.ui.Modal):
    """Modal exibido ao ATIVAR revenda — coleta a % de comissão do revendedor."""

    def __init__(self, *, product_id: str, current_commission: float = 0):
        self._product_id = product_id
        placeholder = str(int(current_commission)) if current_commission else "Ex: 10"
        components = [
            disnake.ui.TextInput(
                label="Comissão do revendedor (%)",
                placeholder=placeholder,
                custom_id="resale_commission",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=5,
            ),
        ]
        super().__init__(
            title="Configurar Revenda",
            components=components,
            custom_id=f"Loja_ResaleCommissionModal:{product_id}",
        )

    async def callback(self, inter: disnake.ModalInteraction):
        product_id = self._product_id
        raw = inter.text_values.get("resale_commission", "").strip().replace(",", ".")

        # ── Valida o número ────────────────────────────────────────────────
        try:
            commission = float(raw)
            if commission < 0 or commission > 100:
                raise ValueError
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Valor inválido. Digite um número entre **0** e **100** (ex: `10` para 10%).",
                ephemeral=True,
            )
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        products = db.get_document("loja_products")
        product = products.get(product_id)
        if not product:
            await inter.response.send_message(
                f"{emoji.wrong} Produto não encontrado.", ephemeral=True
            )
            return

        info = product.get("info", {})
        info["resale"] = True
        info["resale_commission"] = commission
        info["updated_at"] = int(disnake.utils.utcnow().timestamp())
        product["info"] = info
        products[product_id] = product
        db.save_document("loja_products", products)

        from functions.marketplace import invalidate_marketplace_cache
        invalidate_marketplace_cache()

        panel_data = ConfigurarProduto.panel(inter, product_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class ConfigurarProduto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _format_price_brl(value: float) -> str:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return ConfigurarProduto._panel_embed(inter, product_id)
        return ConfigurarProduto._panel_components(inter, product_id)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id)

        info = product.get('info', {})
        raw_desc = info.get('description')
        if raw_desc:
            if len(raw_desc) > 800:
                raw_desc = raw_desc[:800] + "..."
            wrapped_desc = utils.wrap_text_hyphenate(raw_desc, max_width=40)
            if len(wrapped_desc) > 3500:
                wrapped_desc = wrapped_desc[:3500] + "..."
            description = f"\n```{wrapped_desc}```"
        else:
            description = "`Não configurada`"

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        delivery_type = info.get('delivery_type')
        delivery_type_str = "Manual" if delivery_type == "manual" else "Automático"

        # ── Visível no site ────────────────────────────────────────────────
        visible = info.get('visible', False)
        telegram_enabled = info.get('telegram_enabled', False)
        resale = info.get('resale', False)
        resale_commission = info.get('resale_commission', 0)
        resale_str = f"{emoji.correct} Ativado ({resale_commission:g}% comissão)" if resale else f"{emoji.wrong} Desativado"

        container_kwargs = {}
        hex_color = info.get('hex_color')
        if hex_color:
            container_kwargs["accent_colour"] = disnake.Colour(int(hex_color.replace("#", ""), 16))
        elif primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        product_name = product.get('name', 'Sem nome')
        if len(product_name) > 100:
            product_name = product_name[:100] + "..."

        info_text = (
            f"-# Nome: `{product_name}`\n"
            f"-# Tipo de entrega: `{delivery_type_str}`\n"
            f"-# Banner: `{'Configurado' if info.get('banner') else 'Não configurado'}`\n"
            f"-# Visível no site: {'{emoji.correct} Ativado' if visible else f'{emoji.wrong} Desativado'}`\n"
            f"-# Revenda: `{resale_str}`"
        )

        management_text = (
            f"-# Criado em: {utils.format_timestamp(info.get('created_at'))}\n"
            f"-# Última edição: {utils.format_timestamp(info.get('updated_at'))}\n"
            f"-# Compras: `{len(info.get('purchasesIds', []))}` | Faturado: `{utils.format_price_brl(info.get('total_paid', 0))}`\n"
            f"-# Campos: `{len(product.get('campos', {}))}` | Categorias: `{len(product.get('categorias', {}))}` | Cupons: `{len(product.get('cupons', {}))}`"
        )

        header_text = f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Produto > **{product_name[:50]}**"
        info_display = f"**Informações do produto**\n{info_text}"
        desc_display = f"-# Descrição: {description}"

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(header_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(info_display),
                disnake.ui.TextDisplay(desc_display),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Gerenciamento**\n{management_text}"),
                disnake.ui.Separator(),
                # ── Linha 1: ações principais ──────────────────────────────
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Editar", emoji=emoji.edit, custom_id=f"Loja_EditarProduto:{product_id}"),
                    disnake.ui.Button(label="Gerenciar Campos", emoji=emoji.commands, custom_id=f"Loja_CamposProduto:{product_id}"),
                    disnake.ui.Button(label="Botão Extra", emoji=emoji.plus, custom_id=f"LojaBotaoExtra_Painel:{product_id}"),
                    disnake.ui.Button(label="Cupons", emoji=emoji.coupon, custom_id=f"Loja_CuponsProduto:{product_id}"),
                ),
                # ── Linha 2: visibilidade + publicação ─────────────────────
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Visível no site" if not visible else "Ocultar do site",
                        emoji=emoji.off if not visible else emoji.on,
                        style=disnake.ButtonStyle.green if not visible else disnake.ButtonStyle.red,
                        custom_id=f"Loja_ToggleVisivelSite:{product_id}"
                    ),
                    disnake.ui.Button(
                        label="Ativar Revenda" if not resale else "Desativar Revenda",
                        emoji=emoji.off if not resale else emoji.on,
                        style=disnake.ButtonStyle.green if not resale else disnake.ButtonStyle.red,
                        custom_id=f"Loja_ToggleRevenda:{product_id}"
                    ),
                    disnake.ui.Button(label="Publicar mensagem", emoji=emoji.arrow, custom_id=f"Loja_PublicarProduto:{product_id}"),
                    disnake.ui.Button(label="Sincronizar", emoji=emoji.reload, custom_id=f"Loja_AtualizarProduto:{product_id}"),
                    disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Loja_ApagarProduto:{product_id}"),
                ),
                # ── Linha 3: Telegram ───────────────────────────────────────
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar no Telegram" if not telegram_enabled else "Desativar no Telegram",
                        emoji=emoji.off if not telegram_enabled else emoji.on,
                        style=disnake.ButtonStyle.green if not telegram_enabled else disnake.ButtonStyle.red,
                        custom_id=f"Loja_ToggleTelegram:{product_id}"
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Produtos")),
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str) -> dict:
        products = db.get_document("loja_products")
        product = products.get(product_id)

        info = product.get('info', {})

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        embed_kwargs = {}
        hex_color = info.get('hex_color')
        if hex_color:
            embed_kwargs["color"] = int(hex_color.replace("#", ""), 16)
        elif primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

        raw_desc = info.get('description')
        if raw_desc:
            if len(raw_desc) > 800:
                raw_desc = raw_desc[:800] + "..."
            wrapped_desc = utils.wrap_text_hyphenate(raw_desc, max_width=40)
            if len(wrapped_desc) > 1500:
                wrapped_desc = wrapped_desc[:1500] + "..."
            description_block = f"\n```{wrapped_desc}```"
        else:
            description_block = "`Não configurada`"

        delivery_type = info.get('delivery_type')
        delivery_type_str = "Manual" if delivery_type == "manual" else "Automático"
        visible = info.get('visible', False)
        telegram_enabled = info.get('telegram_enabled', False)
        resale = info.get('resale', False)
        resale_commission = info.get('resale_commission', 0)
        resale_str = f"{emoji.correct} Ativado ({resale_commission:g}% comissão)" if resale else f"{emoji.wrong} Desativado"

        compras_qtd = len(info.get('purchasesIds', []))
        total_faturado = utils.format_price_brl(info.get('total_paid', 0))
        campos_qtd = len(product.get('campos', {}))
        categorias_qtd = len(product.get('categorias', {}))
        cupons_qtd = len(product.get('cupons', {}))

        embed_description = (
            f"-# Painel > Loja > Produto > **{product.get('name')}**\n\n"
            f"**Informações do produto**\n"
            f"-# Nome: `{product.get('name')}`\n"
            f"-# Tipo de entrega: `{delivery_type_str}`\n"
            f"-# Visível no site: {f'{emoji.correct} Ativado' if visible else f'{emoji.wrong} Desativado'}`\n"
            f"-# Telegram: `{f'{emoji.correct} Ativado' if telegram_enabled else f'{emoji.wrong} Desativado'}`\n"
            f"-# Revenda: `{resale_str}`\n"
            f"-# Descrição: {description_block}\n\n"
            f"**Gerenciamento do produto**\n"
            f"-# Criado em: {utils.format_timestamp(info.get('created_at'))}\n"
            f"-# Última edição: {utils.format_timestamp(info.get('updated_at'))}\n"
            f"-# Compras realizadas: `{compras_qtd}` | Total faturado: `{total_faturado}`\n"
            f"-# Campos: `{campos_qtd}` | Categorias: `{categorias_qtd}` | Cupons: `{cupons_qtd}`"
        )

        embed = disnake.Embed(description=embed_description, **embed_kwargs)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar", emoji=emoji.edit, custom_id=f"Loja_EditarProduto:{product_id}"),
                disnake.ui.Button(label="Gerenciar Campos", emoji=emoji.commands, custom_id=f"Loja_CamposProduto:{product_id}"),
                disnake.ui.Button(label="Botão Extra", emoji=emoji.plus, custom_id=f"LojaBotaoExtra_Painel:{product_id}"),
                disnake.ui.Button(label="Cupons", emoji=emoji.coupon, custom_id=f"Loja_CuponsProduto:{product_id}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Visível no site" if not visible else "Ocultar do site",
                    emoji=emoji.off if not visible else emoji.on,
                    style=disnake.ButtonStyle.green if not visible else disnake.ButtonStyle.red,
                    custom_id=f"Loja_ToggleVisivelSite:{product_id}"
                ),
                disnake.ui.Button(
                    label="Ativar Revenda" if not resale else "Desativar Revenda",
                    emoji=emoji.off if not resale else emoji.on,
                    style=disnake.ButtonStyle.green if not resale else disnake.ButtonStyle.red,
                    custom_id=f"Loja_ToggleRevenda:{product_id}"
                ),
                disnake.ui.Button(label="Publicar mensagem", emoji=emoji.arrow, custom_id=f"Loja_PublicarProduto:{product_id}"),
                disnake.ui.Button(label="Atualizar", emoji=emoji.reload, custom_id=f"Loja_AtualizarProduto:{product_id}"),
                disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Loja_ApagarProduto:{product_id}"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ativar no Telegram" if not telegram_enabled else "Desativar no Telegram",
                    emoji=emoji.off if not telegram_enabled else emoji.on,
                    style=disnake.ButtonStyle.green if not telegram_enabled else disnake.ButtonStyle.red,
                    custom_id=f"Loja_ToggleTelegram:{product_id}"
                ),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Produtos")),
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        # ── Toggle Telegram ────────────────────────────────────────────────
        if cid.startswith("Loja_ToggleTelegram:"):
            _, product_id = cid.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)

            products = db.get_document("loja_products")
            product = products.get(product_id)
            if product:
                info = product.get("info", {})
                info["telegram_enabled"] = not info.get("telegram_enabled", False)
                info["updated_at"] = int(disnake.utils.utcnow().timestamp())
                product["info"] = info
                products[product_id] = product
                db.save_document("loja_products", products)

            panel_data = ConfigurarProduto.panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        # ── Toggle visível no site ─────────────────────────────────────────
        if cid.startswith("Loja_ToggleVisivelSite:"):
            _, product_id = cid.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)

            products = db.get_document("loja_products")
            product = products.get(product_id)
            if product:
                info = product.get("info", {})
                info["visible"] = not info.get("visible", False)
                info["updated_at"] = int(disnake.utils.utcnow().timestamp())
                product["info"] = info
                products[product_id] = product
                db.save_document("loja_products", products)

            panel_data = ConfigurarProduto.panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        # ── Toggle revenda ─────────────────────────────────────────────────
        if cid.startswith("Loja_ToggleRevenda:"):
            _, product_id = cid.split(":", 1)

            products = db.get_document("loja_products")
            product = products.get(product_id)
            if not product:
                return

            info = product.get("info", {})
            currently_active = info.get("resale", False)

            if currently_active:
                # ── Desativar direto — sem modal ───────────────────────────
                mode = db.get_document("custom_mode").get("mode")
                msg_handler = embed_message if mode == "embed" else message
                await msg_handler.wait(inter, send=False)

                info["resale"] = False
                info["resale_commission"] = 0
                info["updated_at"] = int(disnake.utils.utcnow().timestamp())
                product["info"] = info
                products[product_id] = product
                db.save_document("loja_products", products)

                from functions.marketplace import invalidate_marketplace_cache
                invalidate_marketplace_cache()

                panel_data = ConfigurarProduto.panel(inter, product_id)
                if mode == "embed":
                    await inter.edit_original_message(content=None, **panel_data)
                else:
                    await inter.edit_original_message(**panel_data)
            else:
                # ── Ativar — abre modal para definir % de comissão ─────────
                commission = info.get("resale_commission", 0)
                await inter.response.send_modal(
                    _ResaleCommissionModal(product_id=product_id, current_commission=commission)
                )
            return

        if cid.startswith("Loja_ConfigurarProduto"):
            _, product_id = cid.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            panel_data = ConfigurarProduto.panel(inter, product_id)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)

        elif cid.startswith("Loja_AtualizarProduto:"):
            _, product_id = cid.split(":", 1)
            await inter.response.defer(ephemeral=True)

            products = db.get_document("loja_products")
            product = products.get(product_id)
            if not product:
                await inter.followup.send(content=f"{emoji.wrong} Produto não encontrado.", ephemeral=True)
                return

            total = 0
            updated = 0
            removed = 0
            skipped = 0
            original_messages = product.get("messages") or []
            new_messages = []

            for m in original_messages:
                try:
                    total += 1
                    guild_id = m.get("guild_id")
                    channel_id = m.get("channel_id")
                    message_id = m.get("message_id")
                    mode_saved = m.get("mode")
                    formatted_desc = m.get("formatted_desc", True)

                    if not (guild_id and channel_id and message_id):
                        removed += 1
                        continue
                    if guild_id != inter.guild.id:
                        new_messages.append(m)
                        skipped += 1
                        continue
                    channel = inter.guild.get_channel(int(channel_id))
                    if channel is None:
                        removed += 1
                        continue
                    try:
                        msg = await channel.fetch_message(int(message_id))
                    except disnake.NotFound:
                        removed += 1
                        continue

                    from .send import SendProduct
                    send_cog = None
                    for cog in inter.client.cogs.values():
                        if isinstance(cog, SendProduct):
                            send_cog = cog
                            break
                    if not send_cog:
                        send_cog = SendProduct(inter.bot)

                    if mode_saved == "legacy":
                        embed = send_cog._build_legacy_embed(product, inter.guild, formatted_desc=formatted_desc)
                        components = send_cog._create_buy_button(product_id)
                        await msg.edit(embed=embed, components=components, flags=disnake.MessageFlags(is_components_v2=True))
                        updated += 1
                        new_messages.append(m)
                    elif mode_saved in ("container_outside", "container_inside"):
                        image_inside = (mode_saved == "container_inside")
                        comps = send_cog._build_container(product, image_inside=image_inside, product_id=product_id, formatted_desc=formatted_desc)
                        await msg.edit(components=comps, flags=disnake.MessageFlags(is_components_v2=True))
                        updated += 1
                        new_messages.append(m)
                    else:
                        skipped += 1
                        new_messages.append(m)
                except Exception:
                    skipped += 1
                    new_messages.append(m)

            if len(new_messages) != len(original_messages):
                products[product_id]["messages"] = new_messages
                db.save_document("loja_products", products)

            color_data = db.get_document("custom_colors") or {}
            primary_color_hex = color_data.get("primary")
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

            result = disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sincronização de Produto"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"**Produto:** `{product.get('name')}`\n"
                    f"**Total:** `{total}` | **Atualizadas:** `{updated}` | **Removidas:** `{removed}` | **Ignoradas:** `{skipped}`"
                ),
                **container_kwargs
            )
            await inter.followup.send(components=[result], ephemeral=True, flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Produtos_Select":
            product_id = inter.values[0]
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await inter.response.defer()
                except:
                    pass
            panel_data = ConfigurarProduto.panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)

def setup(bot: commands.Bot):
    bot.add_cog(ConfigurarProduto(bot))