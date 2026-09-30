import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji
from functions.utils import utils
from functions.text_utils import safe_textdisplay, wrap_text
from functions.loja_products import (
    get_product, get_products, save_products, 
    container_kwargs_for_product, embed_kwargs_for_product,
    validate_emoji_string
)
from modules.loja.cart.stock_manager import StockManager
from .configurar import ConfigurarProduto


async def sync_product_messages_silently(bot: commands.Bot, product_id: str):
    """Sincroniza silenciosamente todas as mensagens de um produto"""
    try:
        products = get_products()
        product = products.get(product_id)
        if not product:
            return
        
        messages = product.get("messages", [])
        if not messages:
            return
        
        # Importar SendProduct para usar os métodos de construção
        from .send import SendProduct
        send_product = SendProduct(bot)
        
        for msg_data in messages:
            try:
                guild_id = msg_data.get("guild_id")
                channel_id = msg_data.get("channel_id")
                message_id = msg_data.get("message_id")
                mode = msg_data.get("mode", "legacy")
                formatted_desc = msg_data.get("formatted_desc", True)
                
                guild = bot.get_guild(guild_id)
                if not guild:
                    continue
                
                channel = guild.get_channel(channel_id)
                if not channel:
                    continue
                
                try:
                    msg = await channel.fetch_message(message_id)
                except:
                    continue
                
                # Reconstruir a mensagem baseado no modo
                if mode == "legacy":
                    embed = send_product._build_legacy_embed(product, guild, formatted_desc=formatted_desc)
                    
                    # Criar botões
                    buy_button = send_product._create_buy_button(product_id)
                    components = buy_button
                    await msg.edit(embed=embed, components=components)
                    
                elif mode in ["container_outside", "container_inside"]:
                    image_inside = (mode == "container_inside")
                    container_components = send_product._build_container(
                        product, 
                        image_inside=image_inside, 
                        product_id=product_id, 
                        formatted_desc=formatted_desc
                    )
                    await msg.edit(components=container_components)
            except Exception as e:
                # Ignorar erros silenciosamente
                continue
    except Exception as e:
        # Ignorar erros silenciosamente
        pass


class EditProductPanel:
    """Painel principal de edição de produto"""
    
    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return EditProductPanel._panel_embed(inter, product_id)
        return EditProductPanel._panel_components(inter, product_id)
    
    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str) -> dict:
        product = get_product(product_id)
        if not product:
            return {"components": [disnake.ui.Container(disnake.ui.TextDisplay(f"{emoji.wrong} Produto não encontrado."))]}
        
        product_name = safe_textdisplay(product.get("name", "Produto"), 50)
        container_kwargs = container_kwargs_for_product(product)
        
        header_text = f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Produto > **{product_name}** > **Editar**"
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(header_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Selecione uma opção para editar o produto:"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione uma opção...",
                        custom_id=f"Loja_EditarProduto_Select:{product_id}",
                        options=[
                            disnake.SelectOption(
                                label="Informações Básicas",
                                description="Editar nome, descrição, banner e tipo de entrega",
                                value="basico",
                                emoji=emoji.settings
                            ),
                            disnake.SelectOption(
                                label="Preferências",
                                description="Configurar exibição de opções e vendas",
                                value="preferencias",
                                emoji=emoji.config
                            ),
                            disnake.SelectOption(
                                label="Botão Compra",
                                description="Personalizar texto e emoji do botão de compra",
                                value="botao",
                                emoji=emoji.cart
                            ),
                        ]
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarProduto:{product_id}")),
        ]}
    
    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str) -> dict:
        product = get_product(product_id)
        if not product:
            embed = disnake.Embed(description=f"{emoji.wrong} Produto não encontrado.")
            return {"embed": embed}
        
        product_name = product.get("name", "Produto")
        embed_kwargs = embed_kwargs_for_product(product)
        
        embed = disnake.Embed(
            description=(
                f"-# Painel > Loja > Produto > **{product_name}** > **Editar**\n\n"
                f"Selecione uma opção para editar o produto:"
            ),
            **embed_kwargs
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Selecione uma opção...",
                    custom_id=f"Loja_EditarProduto_Select:{product_id}",
                    options=[
                        disnake.SelectOption(
                            label="Informações Básicas",
                            description="Editar nome, descrição, banner e tipo de entrega",
                            value="basico",
                            emoji=emoji.settings
                        ),
                        disnake.SelectOption(
                            label="Preferências",
                            description="Configurar exibição de opções e vendas",
                            value="preferencias",
                            emoji=emoji.config
                        ),
                        disnake.SelectOption(
                            label="Botão Compra",
                            description="Personalizar texto e emoji do botão de compra",
                            value="botao",
                            emoji=emoji.cart
                        ),
                    ]
                )
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_ConfigurarProduto:{product_id}")),
        ]
        
        return {"embed": embed, "components": components}


class EditBasicInfoModal(disnake.ui.Modal):
    """Modal para editar informações básicas do produto"""
    
    def __init__(self, product_id: str):
        self.product_id = product_id
        
        product = get_product(product_id)
        name_value = product.get("name", "")
        info = product.get("info", {})
        description_value = info.get("description") or ""
        banner_value = info.get("banner") or ""
        hex_value = info.get("hex_color") or ""
        delivery_value = info.get("delivery_type") or "automatic"
        
        components = [
            disnake.ui.Label(
                text="Nome do produto",
                component=disnake.ui.TextInput(
                    placeholder="Digite o nome do produto",
                    custom_id="product_name",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=100,
                    value=name_value,
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
                    value=description_value,
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
                    value=banner_value,
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
                    value=hex_value,
                ),
            ),
            disnake.ui.Label(
                text="Tipo de entrega",
                component=disnake.ui.StringSelect(
                    placeholder="Selecione o tipo de entrega do produto",
                    custom_id="product_delivery_type",
                    required=True,
                    options=[
                        disnake.SelectOption(label="Entrega Automática", description="O produto será entregue automaticamente após o pagamento.", value="automatic", emoji=emoji.reload, default=(delivery_value == "automatic")),
                        disnake.SelectOption(label="Entrega Manual", description="O produto será entregue manualmente pelo suporte.", value="manual", emoji=emoji.hrench2, default=(delivery_value == "manual")),
                    ],
                ),
                description="Define se o produto será entregue automaticamente após o pagamento ou manualmente pelo suporte.",
            ),
        ]
        
        super().__init__(title="Editar Informações Básicas", components=components, custom_id="edit_product_basic_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        
        valores = inter.resolved_values
        
        product_name = valores["product_name"]
        product_description = valores.get("product_description")
        
        delivery_value = valores.get("product_delivery_type", "")
        if isinstance(delivery_value, (list, tuple)):
            product_delivery_type = delivery_value[0] if delivery_value else None
        else:
            product_delivery_type = delivery_value or None
        
        raw_banner = valores.get("product_banner")
        raw_hex = valores.get("product_hex_color")
        
        banner_value = raw_banner if utils.is_valid_url(raw_banner) else None
        hex_value = utils.normalize_hex_color(raw_hex)
        
        products = get_products()
        product = products.get(self.product_id)
        if not product:
            panel_data = ConfigurarProduto.panel(inter, self.product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return
        
        product["name"] = product_name
        info = product.get("info", {})
        info["description"] = product_description
        info["banner"] = banner_value
        info["hex_color"] = hex_value
        info["delivery_type"] = product_delivery_type
        info["updated_at"] = int(disnake.utils.utcnow().timestamp())
        product["info"] = info
        
        products[self.product_id] = product
        save_products(products)
        
        # Sincronizar silenciosamente todas as mensagens
        await sync_product_messages_silently(inter.client, self.product_id)
        
        panel_data = EditProductPanel.panel(inter, self.product_id)
        
        if not inter.response.is_done():
            try:
                await inter.response.defer()
            except:
                pass
        
        if mode == "embed":
            await inter.edit_original_message(
                content=f"{emoji.loading} Carregando...",
                embed=None,
                components=[]
            )
            await inter.edit_original_message(**panel_data)
        else:
            await inter.edit_original_message(
                embed=None,
                components=[disnake.ui.TextDisplay(f"{emoji.loading} Carregando...")],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            if "flags" not in panel_data:
                panel_data["flags"] = disnake.MessageFlags(is_components_v2=True)
            await inter.edit_original_message(**panel_data)


class PreferencesPanel:
    """Painel de preferências do produto (nova versão)"""
    
    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return PreferencesPanel._panel_embed(inter, product_id)
        return PreferencesPanel._panel_components(inter, product_id)
    
    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str) -> dict:
        product = get_product(product_id)
        if not product:
            return {"components": [disnake.ui.Container(disnake.ui.TextDisplay(f"{emoji.wrong} Produto não encontrado."))]}
        
        product_name = safe_textdisplay(product.get("name", "Produto"), 50)
        info = product.get("info", {})
        
        # Obter preferências de exibição (locais do produto)
        display_prefs = info.get("display_preferences", {})
        show_sales = display_prefs.get("show_sales", True)
        show_options = display_prefs.get("show_options", True)
        
        container_kwargs = container_kwargs_for_product(product)
        
        header_text = f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Produto > {product_name} > Editar > **Preferências de Exibição**"
        
        prefs_text = f"""
-# {emoji.information} **Exibir número de opções:** `{'Ativado' if show_options else 'Desativado'}`
-# {emoji.dollar} **Exibir número de vendas:** `{'Ativado' if show_sales else 'Desativado'}`"""
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(header_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(prefs_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Opções",
                        emoji=emoji.on if show_options else emoji.off,
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"Loja_EditarProduto_Pref_Options:{product_id}"
                    ),
                    disnake.ui.Button(
                        label="Vendas",
                        emoji=emoji.on if show_sales else emoji.off,
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"Loja_EditarProduto_Pref_Sales:{product_id}"
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_EditarProduto:{product_id}")),
        ]}
    
    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str) -> dict:
        product = get_product(product_id)
        if not product:
            embed = disnake.Embed(description=f"{emoji.wrong} Produto não encontrado.")
            return {"embed": embed}
        
        product_name = product.get("name", "Produto")
        info = product.get("info", {})
        
        display_prefs = info.get("display_preferences", {})
        show_sales = display_prefs.get("show_sales", True)
        show_options = display_prefs.get("show_options", True)
        
        embed_kwargs = embed_kwargs_for_product(product)
        
        embed = disnake.Embed(
            description=(
                f"-# Painel > Loja > Produto > **{product_name}** > **Editar > Preferências de Exibição**\n\n"
                f"-# {emoji.information} **Exibir número de opções:** `{'Ativado' if show_options else 'Desativado'}`\n"
                f"-# {emoji.dollar} **Exibir número de vendas:** `{'Ativado' if show_sales else 'Desativado'}`\n\n"
            ),
            **embed_kwargs
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Opções",
                    emoji=emoji.on if show_options else emoji.off,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f"Loja_EditarProduto_Pref_Options:{product_id}"
                ),
                disnake.ui.Button(
                    label="Vendas",
                    emoji=emoji.on if show_sales else emoji.off,
                    style=disnake.ButtonStyle.grey,
                    custom_id=f"Loja_EditarProduto_Pref_Sales:{product_id}"
                ),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_EditarProduto:{product_id}")),
        ]
        
        return {"embed": embed, "components": components}


class EditButtonPanel:
    """Painel para editar texto/emoji do botão de compra"""
    
    @staticmethod
    def panel(inter: disnake.MessageInteraction, product_id: str) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return EditButtonPanel._panel_embed(inter, product_id)
        return EditButtonPanel._panel_components(inter, product_id)
    
    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction, product_id: str) -> dict:
        product = get_product(product_id)
        if not product:
            return {"components": [disnake.ui.Container(disnake.ui.TextDisplay(f"{emoji.wrong} Produto não encontrado."))]}
        
        product_name = safe_textdisplay(product.get("name", "Produto"), 50)
        info = product.get("info", {})
        
        # Obter configurações do botão
        button_config = info.get("buy_button", {})
        button_label = button_config.get("label", "Comprar")
        button_emoji_str = button_config.get("emoji", emoji.cart)
        
        container_kwargs = container_kwargs_for_product(product)
        
        header_text = f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Produto > **{product_name}** > **Editar > Botão de Compra**"
        
        current_text = f"""**Configurações atuais do botão:**
-# Texto: `{button_label}`
-# Emoji: {button_emoji_str}

Edite o texto e emoji do botão de compra que aparecerá na mensagem do produto."""
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(header_text),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(current_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Editar Botão", emoji=emoji.edit, custom_id=f"Loja_EditarProduto_Botao_Modal:{product_id}"),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_EditarProduto:{product_id}")),
        ]}
    
    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction, product_id: str) -> dict:
        product = get_product(product_id)
        if not product:
            embed = disnake.Embed(description=f"{emoji.wrong} Produto não encontrado.")
            return {"embed": embed}
        
        product_name = product.get("name", "Produto")
        info = product.get("info", {})
        
        button_config = info.get("buy_button", {})
        button_label = button_config.get("label", "Comprar")
        button_emoji_str = button_config.get("emoji", emoji.cart)
        
        embed_kwargs = embed_kwargs_for_product(product)
        
        embed = disnake.Embed(
            description=(
                f"-# Painel > Loja > Produto > **{product_name}** > **Editar > Botão de Compra**\n\n"
                f"**Configurações atuais do botão:**\n"
                f"-# Texto: `{button_label}`\n"
                f"-# Emoji: {button_emoji_str}\n\n"
                f"Edite o texto e emoji do botão de compra que aparecerá na mensagem do produto."
            ),
            **embed_kwargs
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Botão", emoji=emoji.edit, custom_id=f"Loja_EditarProduto_Botao_Modal:{product_id}"),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"Loja_EditarProduto:{product_id}")),
        ]
        
        return {"embed": embed, "components": components}


class EditButtonModal(disnake.ui.Modal):
    """Modal para editar texto e emoji do botão de compra"""
    
    def __init__(self, product_id: str):
        self.product_id = product_id
        
        product = get_product(product_id)
        info = product.get("info", {})
        button_config = info.get("buy_button", {})
        
        button_label = button_config.get("label", "Comprar")
        button_emoji_str = button_config.get("emoji", emoji.cart)
        
        components = [
            disnake.ui.Label(
                text="Texto do botão",
                component=disnake.ui.TextInput(
                    placeholder="Digite o texto do botão",
                    custom_id="button_label",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    max_length=30,
                    value=button_label,
                ),
            ),
            disnake.ui.Label(
                text="Emoji do botão",
                component=disnake.ui.TextInput(
                    placeholder="Digite o emoji (ex: 🛒 ou <:cart:123456>)",
                    custom_id="button_emoji",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    max_length=100,
                    value=button_emoji_str if isinstance(button_emoji_str, str) else "",
                ),
                description="Pode ser um emoji Unicode ou um emoji customizado do servidor"
            ),
        ]
        
        super().__init__(title="Editar Botão de Compra", components=components, custom_id="edit_button_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        
        valores = inter.resolved_values
        
        button_label = valores.get("button_label", "Comprar")
        button_emoji_raw = valores.get("button_emoji", "").strip()
        
        # Validar emoji antes de salvar
        if button_emoji_raw:
            # Obter mensagem de erro detalhada da validação
            from functions.utils import utils
            validation = utils.validate_emoji_for_components(button_emoji_raw)
            
            if not validation["valid"]:
                # Emoji inválido - usar mensagem de erro específica
                error_msg = validation.get("error", "Emoji inválido! Por favor, use um emoji Unicode válido ou um emoji customizado do servidor.")
                panel_data = EditButtonPanel.panel(inter, self.product_id)
                if mode == "embed":
                    await inter.edit_original_message(
                        content=None,
                        embed=disnake.Embed(
                            description=f"{emoji.wrong} {error_msg}",
                            color=disnake.Color.red()
                        ),
                        components=panel_data.get("components", [])
                    )
                else:
                    product = get_product(self.product_id)
                    error_component = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.wrong} {error_msg}"),
                        **container_kwargs_for_product(product) if product else {}
                    )
                    await inter.edit_original_message(
                        components=[error_component] + panel_data.get("components", []),
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                return
            
            # Se passou na validação, usar validate_emoji_string para verificar acesso do bot
            button_emoji = validate_emoji_string(inter.bot, button_emoji_raw)
            if button_emoji is None:
                # Emoji válido mas bot não tem acesso
                panel_data = EditButtonPanel.panel(inter, self.product_id)
                if mode == "embed":
                    await inter.edit_original_message(
                        content=None,
                        embed=disnake.Embed(
                            description=f"{emoji.wrong} Emoji customizado não encontrado no servidor. Certifique-se de que o bot tem acesso ao emoji.",
                            color=disnake.Color.red()
                        ),
                        components=panel_data.get("components", [])
                    )
                else:
                    product = get_product(self.product_id)
                    error_component = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.wrong} Emoji customizado não encontrado no servidor. Certifique-se de que o bot tem acesso ao emoji."),
                        **container_kwargs_for_product(product) if product else {}
                    )
                    await inter.edit_original_message(
                        components=[error_component] + panel_data.get("components", []),
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                return
        else:
            # Se não forneceu emoji, usar o padrão
            button_emoji = emoji.cart
        
        products = get_products()
        product = products.get(self.product_id)
        if not product:
            panel_data = EditProductPanel.panel(inter, self.product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return
        
        info = product.get("info", {})
        button_config = info.get("buy_button", {})
        button_config["label"] = button_label
        button_config["emoji"] = button_emoji
        info["buy_button"] = button_config
        info["updated_at"] = int(disnake.utils.utcnow().timestamp())
        product["info"] = info
        
        products[self.product_id] = product
        save_products(products)
        
        # Sincronizar silenciosamente todas as mensagens
        await sync_product_messages_silently(inter.client, self.product_id)
        
        panel_data = EditButtonPanel.panel(inter, self.product_id)
        
        if not inter.response.is_done():
            try:
                await inter.response.defer()
            except:
                pass
        
        if mode == "embed":
            await inter.edit_original_message(
                content=f"{emoji.loading} Carregando...",
                embed=None,
                components=[]
            )
            await inter.edit_original_message(**panel_data)
        else:
            await inter.edit_original_message(
                embed=None,
                components=[disnake.ui.TextDisplay(f"{emoji.loading} Carregando...")],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
            if "flags" not in panel_data:
                panel_data["flags"] = disnake.MessageFlags(is_components_v2=True)
            await inter.edit_original_message(**panel_data)


class EditProduct(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        
        # Select de opções
        if custom_id.startswith("Loja_EditarProduto_Select:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return
            
            value = inter.values[0] if inter.values else None
            
            if value == "basico":
                await inter.response.send_modal(EditBasicInfoModal(product_id))
            elif value == "preferencias":
                await inter.response.defer()
                mode = db.get_document("custom_mode").get("mode")
                await (embed_message if mode == "embed" else message).wait(inter, send=False)
                panel_data = PreferencesPanel.panel(inter, product_id)
                if mode == "embed":
                    await inter.edit_original_message(content=None, **panel_data)
                else:
                    await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            elif value == "botao":
                await inter.response.defer()
                mode = db.get_document("custom_mode").get("mode")
                await (embed_message if mode == "embed" else message).wait(inter, send=False)
                panel_data = EditButtonPanel.panel(inter, product_id)
                if mode == "embed":
                    await inter.edit_original_message(content=None, **panel_data)
                else:
                    await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return
    
    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        
        # Verificar se é exatamente o formato "Loja_EditarProduto:product_id" sem sufixos
        if custom_id.startswith("Loja_EditarProduto:") and not custom_id.startswith("Loja_EditarProduto_Basico:") and not custom_id.startswith("Loja_EditarProduto_Preferencias:") and not custom_id.startswith("Loja_EditarProduto_Botao:") and not custom_id.startswith("Loja_EditarProduto_Pref_") and not custom_id.startswith("Loja_EditarProduto_Select:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if product_id:
                mode = db.get_document("custom_mode").get("mode")
                await (embed_message if mode == "embed" else message).wait(inter, send=False)
                panel_data = EditProductPanel.panel(inter, product_id)
                if mode == "embed":
                    await inter.edit_original_message(content=None, **panel_data)
                else:
                    await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
                return
        
        # Informações básicas
        if custom_id.startswith("Loja_EditarProduto_Basico:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return
            await inter.response.send_modal(EditBasicInfoModal(product_id))
            return
        
        # Preferências
        if custom_id.startswith("Loja_EditarProduto_Preferencias:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel_data = PreferencesPanel.panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return
        
        # Toggle preferências
        if custom_id.startswith("Loja_EditarProduto_Pref_Sales:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return
            await inter.response.defer(ephemeral=True)
            products = get_products()
            product = products.get(product_id)
            if product:
                info = product.get("info", {})
                display_prefs = info.get("display_preferences", {})
                display_prefs["show_sales"] = not display_prefs.get("show_sales", True)
                info["display_preferences"] = display_prefs
                info["updated_at"] = int(disnake.utils.utcnow().timestamp())
                product["info"] = info
                products[product_id] = product
                save_products(products)
                # Sincronizar silenciosamente todas as mensagens
                await sync_product_messages_silently(inter.client, product_id)
            mode = db.get_document("custom_mode").get("mode")
            panel_data = PreferencesPanel.panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(**panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return
        
        if custom_id.startswith("Loja_EditarProduto_Pref_Options:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return
            await inter.response.defer(ephemeral=True)
            products = get_products()
            product = products.get(product_id)
            if product:
                info = product.get("info", {})
                display_prefs = info.get("display_preferences", {})
                display_prefs["show_options"] = not display_prefs.get("show_options", True)
                info["display_preferences"] = display_prefs
                info["updated_at"] = int(disnake.utils.utcnow().timestamp())
                product["info"] = info
                products[product_id] = product
                save_products(products)
                # Sincronizar silenciosamente todas as mensagens
                await sync_product_messages_silently(inter.client, product_id)
            mode = db.get_document("custom_mode").get("mode")
            panel_data = PreferencesPanel.panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(**panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return
        
        # Botão de compra
        if custom_id.startswith("Loja_EditarProduto_Botao:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel_data = EditButtonPanel.panel(inter, product_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            return
        
        # Modal do botão
        if custom_id.startswith("Loja_EditarProduto_Botao_Modal:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return
            await inter.response.send_modal(EditButtonModal(product_id))
            return
        


def setup(bot: commands.Bot):
    bot.add_cog(EditProduct(bot))
