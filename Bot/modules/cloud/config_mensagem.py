import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils
from .container_utils import ContainerUtils

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

class EditButtonModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        self.data = data
        
        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        current_style_en = data.get("style", "green")
        current_style_pt = next((pt for pt, en in color_map_pt_to_en.items() if en == current_style_en), "verde")

        components = [
            disnake.ui.TextInput(label="Texto do Botão", custom_id="label", value=data.get("label"), max_length=30, required=True, placeholder="Verificar"),
            disnake.ui.TextInput(label="Emoji do Botão (Opcional)", custom_id="emoji", value=data.get("emoji"), required=False, max_length=100, placeholder="✅ ou <:nome:ID>"),
            disnake.ui.TextInput(label="Estilo (verde, cinza, vermelho, azul)", custom_id="style", value=current_style_pt, max_length=10, required=True, placeholder="Ex: verde"),
        ]
        super().__init__(title="Editar Botão de Verificação", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        cloud_config = db.get_document("cloud_data") or {}
        if "message_verify" not in cloud_config:
            cloud_config["message_verify"] = {}
        if "button" not in cloud_config["message_verify"]:
            cloud_config["message_verify"]["button"] = {}

        option_emoji = inter.text_values["emoji"]
        # Validar emoji e usar fallback se inválido
        option_emoji = get_validated_emoji(option_emoji)

        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        style_pt = inter.text_values.get("style", "verde").lower()
        style_en = color_map_pt_to_en.get(style_pt, "green")
        
        cloud_config["message_verify"]["button"]["label"] = inter.text_values["label"]
        cloud_config["message_verify"]["button"]["emoji"] = option_emoji
        cloud_config["message_verify"]["button"]["style"] = style_en
        db.save_document("cloud_data", cloud_config)

        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter))
        else:
            embed, components = MessageEditView_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditEmbedModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Título", custom_id="title", value=data.get("title"), max_length=256, placeholder="Verificação", required=True),
            disnake.ui.TextInput(label="Descrição", custom_id="description", value=data.get("description"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para se verificar...", required=False),
            disnake.ui.TextInput(label="URL da Imagem/Banner", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/banner.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Conteúdo: Embed", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        cloud_config = db.get_document("cloud_data") or {}
        if "message_verify" not in cloud_config:
            cloud_config["message_verify"] = {}
        if "embed" not in cloud_config["message_verify"]:
            cloud_config["message_verify"]["embed"] = {}

        new_data = inter.text_values.copy()
        
        for key in ["color", "image_url", "thumbnail_url", "description"]:
             if key in new_data and not new_data[key]:
                cloud_config["message_verify"]["embed"].pop(key, None)
                del new_data[key]

        cloud_config["message_verify"]["embed"].update(new_data)
        db.save_document("cloud_data", cloud_config)

        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter))
        else:
            embed, components = MessageEditView_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditContentModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=2000, placeholder="Clique no botão abaixo para se verificar...", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
        ]
        super().__init__(title="Editar Conteúdo: Texto Simples", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        cloud_config = db.get_document("cloud_data") or {}
        if "message_verify" not in cloud_config:
            cloud_config["message_verify"] = {}
        if "content" not in cloud_config["message_verify"]:
            cloud_config["message_verify"]["content"] = {}

        new_data = inter.text_values.copy()
        for key in ["image_url", "content"]:
            if key in new_data and not new_data[key]:
                cloud_config["message_verify"]["content"].pop(key, None)
                del new_data[key]

        cloud_config["message_verify"]["content"].update(new_data)
        db.save_document("cloud_data", cloud_config)
        
        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter))
        else:
            embed, components = MessageEditView_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditContainerModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para se verificar...", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Conteúdo: Container", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        cloud_config = db.get_document("cloud_data") or {}
        if "message_verify" not in cloud_config:
            cloud_config["message_verify"] = {}
        if "container" not in cloud_config["message_verify"]:
            cloud_config["message_verify"]["container"] = {}

        new_data = inter.text_values.copy()
        
        for key in ["color", "image_url", "thumbnail_url", "content"]:
            if key in new_data and not new_data[key]:
                cloud_config["message_verify"]["container"].pop(key, None)
                del new_data[key]

        cloud_config["message_verify"]["container"].update(new_data)
        db.save_document("cloud_data", cloud_config)

        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter))
        else:
            embed, components = MessageEditView_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class ExternalSendModal(disnake.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        components = [
            disnake.ui.TextInput(label="ID do Servidor", custom_id="guild_id", placeholder="Cole o ID do servidor de destino", required=True),
            disnake.ui.TextInput(label="ID do Canal", custom_id="channel_id", placeholder="Cole o ID do canal de texto de destino", required=True),
        ]
        super().__init__(title="Enviar para Outro Servidor", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        guild_id_str = inter.text_values["guild_id"]
        channel_id_str = inter.text_values["channel_id"]

        try:
            guild_id = int(guild_id_str)
            channel_id = int(channel_id_str)
        except ValueError:
            await inter.edit_original_message("IDs inválidos. Por favor, insira apenas números.")
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            await inter.edit_original_message(f"Não foi possível encontrar o servidor com ID `{guild_id}`. Verifique se o bot principal está nesse servidor.")
            return

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, disnake.TextChannel):
            await inter.edit_original_message(f"Não foi possível encontrar o canal de texto com ID `{channel_id}` no servidor `{guild.name}`.")
            return
        
        # Reutiliza a mesma lógica de construção e envio da channel_select
        cloud_config = db.get_document("cloud_data") or {}
        message_config = cloud_config.get("message_verify", {})
        
        # A função _send_verification_message foi criada para evitar duplicação de código
        success, error_message = await _send_verification_message(channel, message_config)

        if success:
            await inter.edit_original_message(content=f"Mensagem de verificação enviada para {channel.mention} em `{guild.name}`.")
        else:
            await inter.edit_original_message(content=error_message)


# --- Views ---

def MessageEditView_components(inter: disnake.Interaction) -> list:
    cloud_config = db.get_document("cloud_data") or {}
    message_config = cloud_config.get("message_verify", {})
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    style = message_config.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(message_config.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(message_config.get("embed", {}).get("title"))
    elif style == "content":
        content_data = message_config.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(message_config.get("container", {}).get("content"))
    
    preview_enabled = button_configured and content_configured

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if button_configured else emoji.wrong} **Botão:** {'`Configurado`' if button_configured else '`Não Configurado`'}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    main_container_children = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# AmyCloud > **Configurar Mensagem**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id="CloudMsgEdit_CycleStyle"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id="CloudMsgEdit_EditButton"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="CloudMsgEdit_EditContent"),
        ),
    ]

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(*main_container_children, **container_kwargs)
    
    action_row_buttons = [
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_MainPanel"),
        disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="CloudMsgEdit_Preview", disabled=not preview_enabled)
    ]

    publish_enabled = button_configured and content_configured
    if publish_enabled:
        action_row_buttons.append(
            disnake.ui.Button(label="Publicar", style=disnake.ButtonStyle.green, emoji=emoji.double_check, custom_id="CloudMsgEdit_Send")
        )

    buttons = disnake.ui.ActionRow(*action_row_buttons)

    return [container, buttons]

def MessageEditView_embed(inter: disnake.Interaction):
    cloud_config = db.get_document("cloud_data") or {}
    message_config = cloud_config.get("message_verify", {})

    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    style = message_config.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(message_config.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(message_config.get("embed", {}).get("title"))
    elif style == "content":
        content_data = message_config.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(message_config.get("container", {}).get("content"))
    
    preview_enabled = button_configured and content_configured

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if button_configured else emoji.wrong} **Botão:** {'`Configurado`' if button_configured else '`Não Configurado`'}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurar Mensagem de Verificação",
        description=status_text,
        **embed_kwargs
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    action_row_buttons = [
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_MainPanel"),
        disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="CloudMsgEdit_Preview", disabled=not preview_enabled)
    ]

    publish_enabled = button_configured and content_configured
    if publish_enabled:
        action_row_buttons.append(
            disnake.ui.Button(label="Publicar", style=disnake.ButtonStyle.green, emoji=emoji.double_check, custom_id="CloudMsgEdit_Send")
        )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id="CloudMsgEdit_CycleStyle"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id="CloudMsgEdit_EditButton"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="CloudMsgEdit_EditContent"),
        ),
        disnake.ui.ActionRow(*action_row_buttons)
    ]

    return embed, components

def SendPanelView_components(bot):
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    main_container_children = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# AmyCloud > **Publicar Mensagem**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay("Selecione o canal onde a mensagem de verificação deve ser enviada."),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Selecione um canal para enviar a mensagem",
                channel_types=[disnake.ChannelType.text],
                custom_id="CloudSend_ChannelSelect"
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Enviar em Outro Servidor", style=disnake.ButtonStyle.grey, emoji=emoji.web, custom_id="CloudSend_External")
        )
    ]
    
    container = disnake.ui.Container(*main_container_children, **container_kwargs)
    return [container]

def SendPanelView_embed(bot):
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Publicar Mensagem de Verificação",
        description="Selecione o canal onde a mensagem de verificação deve ser enviada.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Selecione um canal para enviar a mensagem",
                channel_types=[disnake.ChannelType.text],
                custom_id="CloudSend_ChannelSelect"
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Enviar em Outro Servidor", style=disnake.ButtonStyle.grey, emoji=emoji.web, custom_id="CloudSend_External")
        )
    ]
    
    return embed, components

async def _send_verification_message(channel: disnake.TextChannel, message_config: dict) -> tuple[bool, str | None]:
    style = message_config.get("message_style", "embed")
    send_kwargs = {}
    
    if style == "embed":
        embed_data = message_config.get("embed", {})
        normalized_data = utils.normalize_embed_data(embed_data)
        embed = disnake.Embed.from_dict(normalized_data)
        send_kwargs["embed"] = embed
    elif style == "content":
        content_data = message_config.get("content", {})
        send_kwargs["content"] = content_data.get("content")
        if "image_url" in content_data and content_data["image_url"]:
            try:
                send_kwargs["file"] = await utils.url_to_file(content_data["image_url"], "image.png")
            except Exception as e:
                # Se falhar ao baixar a imagem, continua sem ela
                print(f"Aviso: Falha ao baixar imagem para mensagem de verificação: {e}")
                # Não adiciona o arquivo, mas continua com o envio da mensagem
    elif style == "container":
        data = message_config.get("container", {})
        container = ContainerUtils.montar_container(
            conteudo=data.get("content"), 
            imagem_url=data.get("image_url"), 
            cor_hex=data.get("color"),
            thumbnail_url=data.get("thumbnail_url")
        )
        button_data = message_config.get("button", {})
        style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}
        button = disnake.ui.Button(
            label=button_data.get("label", "Verificar"),
            style=style_map.get(button_data.get("style", "green")),
            emoji=get_validated_emoji(button_data.get("emoji")),
            custom_id="Cloud_GetAuthLink"
        )
        action_row = disnake.ui.ActionRow(button)
        send_kwargs["components"] = [container, action_row]
        send_kwargs["flags"] = disnake.MessageFlags(is_components_v2=True)
        try:
            await channel.send(**send_kwargs)
            return True, None
        except disnake.Forbidden:
            return False, "Não tenho permissão para enviar mensagens nesse canal."
        except Exception as e:
            return False, f"Ocorreu um erro ao enviar a mensagem: {e}"

    button_data = message_config.get("button", {})
    style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}
    button = disnake.ui.Button(
        label=button_data.get("label", "Verificar"),
        style=style_map.get(button_data.get("style", "green")),
        emoji=get_validated_emoji(button_data.get("emoji")),
        custom_id="Cloud_GetAuthLink"
    )
    
    view = disnake.ui.View(timeout=None)
    view.add_item(button)
    send_kwargs["view"] = view
    
    try:
        # Prevenção de loop infinito: verifica se a última mensagem enviada no canal
        # já é uma mensagem de verificação do AmyCloud enviada recentemente.
        try:
            async for msg in channel.history(limit=5):
                if msg.author.id == bot.user.id:
                    # Verificar se tem o botão de verificação
                    for row in msg.components:
                        for component in row.children:
                            if isinstance(component, disnake.Button) and component.custom_id == "Cloud_GetAuthLink":
                                # Já existe uma mensagem de verificação recente
                                return True, "Uma mensagem de verificação já existe neste canal."
        except Exception:
            pass

        await channel.send(**send_kwargs)
        return True, None
    except disnake.Forbidden:
        return False, "Não tenho permissão para enviar mensagens nesse canal."
    except Exception as e:
        return False, f"Ocorreu um erro ao enviar a mensagem: {e}"

async def show_panel(inter: disnake.Interaction):
    mode = db.get_document("custom_mode").get("mode")

    if mode == "embed":
        await embed_message.wait(inter)
        embed, components = MessageEditView_embed(inter)
        await inter.edit_original_message(content=None, embed=embed, components=components)
    else:
        await message.wait(inter)
        components = MessageEditView_components(inter)
        await inter.edit_original_message(content=None, components=components)

async def show_send_panel(inter: disnake.Interaction, bot):
    mode = db.get_document("custom_mode").get("mode")
    
    # Este painel deve ser ephemeral e independente do painel principal
    if not inter.response.is_done():
        await inter.response.defer(ephemeral=True)

    if mode == "embed":
        embed, components = SendPanelView_embed(bot)
        await inter.followup.send(embed=embed, components=components, ephemeral=True)
    else:
        components = SendPanelView_components(bot)
        await inter.followup.send(components=components, ephemeral=True)
