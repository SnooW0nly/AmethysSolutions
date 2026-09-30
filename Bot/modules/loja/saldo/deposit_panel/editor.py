"""
Editor do Painel de Depósito
Similar ao editor de mensagens do sistema cloud
"""
import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils


# --- Helper Functions ---

def get_validated_emoji(emoji_value: str | None) -> str | None:
    """
    Valida um emoji e retorna emoji.double_check se inválido.
    
    Args:
        emoji_value: Valor do emoji a ser validado
        
    Returns:
        Emoji validado ou emoji.double_check se inválido, ou None se vazio
    """
    if not emoji_value:
        return None
    
    validation = utils.validate_emoji_for_components(emoji_value)
    if not validation["valid"]:
        return emoji.double_check
    
    # Converter para string apropriada
    if isinstance(validation["emoji"], disnake.PartialEmoji):
        return str(validation["emoji"])
    else:
        return validation["emoji"]


# --- Modals ---

class DepositAmountModal(disnake.ui.Modal):
    """Modal para o usuário inserir o valor do depósito"""
    
    def __init__(self, min_amount: float, max_amount: float, thread_id: int):
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.thread_id = thread_id
        
        components = [
            disnake.ui.TextInput(
                label=f"Valor do Depósito (R$ {min_amount:.2f} - R$ {max_amount:.2f})",
                custom_id="amount",
                placeholder=f"Ex: {min_amount:.2f}",
                required=True,
                max_length=10
            )
        ]
        super().__init__(title="Definir Valor do Depósito", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        amount_str = inter.text_values["amount"].replace(",", ".").strip()
        
        try:
            amount = float(amount_str)
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Valor inválido. Use apenas números.",
                ephemeral=True
            )
            return
        
        if amount < self.min_amount:
            await inter.response.send_message(
                f"{emoji.wrong} Valor mínimo: R$ {self.min_amount:.2f}",
                ephemeral=True
            )
            return
        
        if amount > self.max_amount:
            await inter.response.send_message(
                f"{emoji.wrong} Valor máximo: R$ {self.max_amount:.2f}",
                ephemeral=True
            )
            return
        
        # Obter configuração para calcular bonus
        config = db.get_document("loja_saldo_config") or {}
        bonus_config = config.get("bonus", {})
        bonus_type = bonus_config.get("type", "disabled")
        bonus_value = bonus_config.get("value", 0)
        
        bonus = 0
        if bonus_type == "percentage" and bonus_value > 0:
            bonus = amount * (bonus_value / 100)
        elif bonus_type == "fixed" and bonus_value > 0:
            bonus = bonus_value
        
        total = amount + bonus
        
        # Obter cor
        color_data = db.get_document("custom_colors") or {}
        primary_color = color_data.get("primary")
        
        bonus_text = ""
        if bonus > 0:
            bonus_text = f"\n{emoji.correct} **Bônus:** `+R$ {bonus:.2f}`\n{emoji.wallet} **Total a Creditar:** `R$ {total:.2f}`"
        
        # Ir direto para o pagamento (sem mensagem de confirmação intermediária)
        # Simular click no botão deposit_confirm chamando o handler diretamente
        from modules.loja.saldo.deposit_panel.deposit_handler import DepositHandler
        
        # Buscar o cog do deposit handler
        bot = inter.bot
        deposit_cog = bot.get_cog("DepositHandler")
        
        if deposit_cog:
            await deposit_cog._process_deposit_payment(inter, amount)
        else:
            await inter.response.send_message(
                f"{emoji.wrong} Erro ao processar depósito. Tente novamente.",
                ephemeral=True
            )


class EditButtonModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        self.data = data
        
        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        current_style_en = data.get("style", "green")
        current_style_pt = next((pt for pt, en in color_map_pt_to_en.items() if en == current_style_en), "verde")

        components = [
            disnake.ui.TextInput(label="Texto do Botão", custom_id="label", value=data.get("label"), max_length=30, required=True, placeholder="Depositar"),
            disnake.ui.TextInput(label="Emoji do Botão (Opcional)", custom_id="emoji", value=data.get("emoji"), required=False, max_length=100, placeholder="💰 ou <:nome:ID>"),
            disnake.ui.TextInput(label="Estilo (verde, cinza, vermelho, azul)", custom_id="style", value=current_style_pt, max_length=10, required=True, placeholder="Ex: verde"),
        ]
        super().__init__(title="Editar Botão de Depósito", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("loja_saldo_config") or {}
        if "deposit_panel" not in config:
            config["deposit_panel"] = {}
        if "button" not in config["deposit_panel"]:
            config["deposit_panel"]["button"] = {}

        option_emoji = inter.text_values["emoji"]
        option_emoji = get_validated_emoji(option_emoji)

        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        style_pt = inter.text_values.get("style", "verde").lower()
        style_en = color_map_pt_to_en.get(style_pt, "green")
        
        config["deposit_panel"]["button"]["label"] = inter.text_values["label"]
        config["deposit_panel"]["button"]["emoji"] = option_emoji
        config["deposit_panel"]["button"]["style"] = style_en
        db.save_document("loja_saldo_config", config)

        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        if mode == "components":
            await inter.response.edit_message(components=deposit_panel_editor_components(inter, config)["components"])
        else:
            data = deposit_panel_editor_embed(inter, config)
            await inter.response.edit_message(content=None, embed=data["embed"], components=data["components"])


class EditEmbedModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Título", custom_id="title", value=data.get("title"), max_length=256, placeholder="Depositar Saldo", required=True),
            disnake.ui.TextInput(label="Descrição", custom_id="description", value=data.get("description"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para depositar...", required=False),
            disnake.ui.TextInput(label="URL da Imagem/Banner", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/banner.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Conteúdo: Embed", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("loja_saldo_config") or {}
        if "deposit_panel" not in config:
            config["deposit_panel"] = {}
        if "embed" not in config["deposit_panel"]:
            config["deposit_panel"]["embed"] = {}

        new_data = inter.text_values.copy()
        
        for key in ["color", "image_url", "thumbnail_url", "description"]:
             if key in new_data and not new_data[key]:
                config["deposit_panel"]["embed"].pop(key, None)
                del new_data[key]

        config["deposit_panel"]["embed"].update(new_data)
        db.save_document("loja_saldo_config", config)

        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        if mode == "components":
            await inter.response.edit_message(components=deposit_panel_editor_components(inter, config)["components"])
        else:
            data = deposit_panel_editor_embed(inter, config)
            await inter.response.edit_message(content=None, embed=data["embed"], components=data["components"])


class EditContentModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=2000, placeholder="Clique no botão abaixo para depositar...", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
        ]
        super().__init__(title="Editar Conteúdo: Texto Simples", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("loja_saldo_config") or {}
        if "deposit_panel" not in config:
            config["deposit_panel"] = {}
        if "content" not in config["deposit_panel"]:
            config["deposit_panel"]["content"] = {}

        new_data = inter.text_values.copy()
        for key in ["image_url", "content"]:
            if key in new_data and not new_data[key]:
                config["deposit_panel"]["content"].pop(key, None)
                del new_data[key]

        config["deposit_panel"]["content"].update(new_data)
        db.save_document("loja_saldo_config", config)
        
        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        if mode == "components":
            await inter.response.edit_message(components=deposit_panel_editor_components(inter, config)["components"])
        else:
            data = deposit_panel_editor_embed(inter, config)
            await inter.response.edit_message(content=None, embed=data["embed"], components=data["components"])


class EditContainerModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para depositar...", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Conteúdo: Container", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("loja_saldo_config") or {}
        if "deposit_panel" not in config:
            config["deposit_panel"] = {}
        if "container" not in config["deposit_panel"]:
            config["deposit_panel"]["container"] = {}

        new_data = inter.text_values.copy()
        
        for key in ["color", "image_url", "thumbnail_url", "content"]:
            if key in new_data and not new_data[key]:
                config["deposit_panel"]["container"].pop(key, None)
                del new_data[key]

        config["deposit_panel"]["container"].update(new_data)
        db.save_document("loja_saldo_config", config)

        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        if mode == "components":
            await inter.response.edit_message(components=deposit_panel_editor_components(inter, config)["components"])
        else:
            data = deposit_panel_editor_embed(inter, config)
            await inter.response.edit_message(content=None, embed=data["embed"], components=data["components"])


# --- Views ---

def deposit_panel_editor_components(inter: disnake.MessageInteraction, config: dict) -> dict:
    """Retorna o editor de painel de depósito no modo container v2"""
    color_data = db.get_document("custom_colors")
    primary_color_hex = color_data.get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
    
    deposit_panel = config.get("deposit_panel", {})
    style = deposit_panel.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(deposit_panel.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(deposit_panel.get("embed", {}).get("title"))
    elif style == "content":
        content_data = deposit_panel.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(deposit_panel.get("container", {}).get("content"))
    
    preview_enabled = button_configured and content_configured

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if button_configured else emoji.wrong} **Botão:** {'`Configurado`' if button_configured else '`Não Configurado`'}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    main_container_children = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Sistema de Saldo > **Painel de Depósito**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id="DepositPanel_CycleStyle"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id="DepositPanel_EditButton"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="DepositPanel_EditContent"),
        ),
    ]

    container = disnake.ui.Container(*main_container_children, **container_kwargs)
    
    action_row_buttons = [
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Saldo_Panel"),
        disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="DepositPanel_Preview", disabled=not preview_enabled)
    ]

    publish_enabled = button_configured and content_configured
    if publish_enabled:
        action_row_buttons.append(
            disnake.ui.Button(label="Publicar", style=disnake.ButtonStyle.green, emoji=emoji.double_check, custom_id="DepositPanel_Send")
        )

    buttons = disnake.ui.ActionRow(*action_row_buttons)

    return {"components": [container, buttons]}


def deposit_panel_editor_embed(inter: disnake.MessageInteraction, config: dict) -> dict:
    """Retorna o editor de painel de depósito no modo embed"""
    color_data = db.get_document("custom_colors")
    primary_color_hex = color_data.get("primary")
    
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
    
    deposit_panel = config.get("deposit_panel", {})
    style = deposit_panel.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(deposit_panel.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(deposit_panel.get("embed", {}).get("title"))
    elif style == "content":
        content_data = deposit_panel.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(deposit_panel.get("container", {}).get("content"))
    
    preview_enabled = button_configured and content_configured
    
    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if button_configured else emoji.wrong} **Botão:** {'`Configurado`' if button_configured else '`Não Configurado`'}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    embed = disnake.Embed(
        title=f"Configurar Painel de Depósito",
        description=status_text,
        **embed_kwargs
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    action_row_buttons = [
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Saldo_Panel"),
        disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="DepositPanel_Preview", disabled=not preview_enabled)
    ]

    publish_enabled = button_configured and content_configured
    if publish_enabled:
        action_row_buttons.append(
            disnake.ui.Button(label="Publicar", style=disnake.ButtonStyle.green, emoji=emoji.double_check, custom_id="DepositPanel_Send")
        )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id="DepositPanel_CycleStyle"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id="DepositPanel_EditButton"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="DepositPanel_EditContent"),
        ),
        disnake.ui.ActionRow(*action_row_buttons)
    ]

    return {"embed": embed, "components": components}


async def show_panel(inter: disnake.Interaction, config: dict):
    """Exibe o painel de edição do depósito"""
    mode = db.get_document("custom_mode").get("mode")

    if mode == "embed":
        await embed_message.wait(inter)
        data = deposit_panel_editor_embed(inter, config)
        await inter.edit_original_message(content=None, embed=data["embed"], components=data["components"])
    else:
        await message.wait(inter)
        data = deposit_panel_editor_components(inter, config)
        await inter.edit_original_message(content=None, components=data["components"])
