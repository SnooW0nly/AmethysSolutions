import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

def parse_hex_color(s):
    s = (s or "").strip().lstrip("#")
    if len(s) == 6:
        try: return disnake.Color(int(s, 16))
        except ValueError: return None
    return None

# --- Modals de Edição ---

class EditEmbedModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, data: dict):
        self.panel_id = panel_id
        components = [
            disnake.ui.TextInput(label="Título", custom_id="title", value=data.get("title"), max_length=256, placeholder="Suporte Geral", required=True),
            disnake.ui.TextInput(label="Descrição", custom_id="description", value=data.get("description"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para ser atendido por nossa equipe.", required=False),
            disnake.ui.TextInput(label="URL da Imagem/Banner", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/banner.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Estilo: Embed", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        if self.panel_id in config.get("panels", {}):
            if "embed" not in config["panels"][self.panel_id]:
                config["panels"][self.panel_id]["embed"] = {}

            new_data = inter.text_values.copy()
            # Se o campo de cor for deixado em branco, removemos a chave
            # para que o sistema use a cor padrão ao invés de salvar uma string vazia.
            if "color" in new_data and not new_data["color"]:
                config["panels"][self.panel_id]["embed"].pop("color", None)
                del new_data["color"]
            if "image_url" in new_data and not new_data["image_url"]:
                config["panels"][self.panel_id]["embed"].pop("image_url", None)
                del new_data["image_url"]
            if "thumbnail_url" in new_data and not new_data["thumbnail_url"]:
                config["panels"][self.panel_id]["embed"].pop("thumbnail_url", None)
                del new_data["thumbnail_url"]
            if "description" in new_data and not new_data["description"]:
                config["panels"][self.panel_id]["embed"].pop("description", None)
                del new_data["description"]

            config["panels"][self.panel_id]["embed"].update(new_data)
            config["panels"][self.panel_id]["has_pending_changes"] = True
            db.save_document("tickets_config", config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter, self.panel_id))
        else:
            embed, components = MessageEditView_embed(inter, self.panel_id)
            await inter.response.edit_message(content=None, embed=embed, components=components)


class EditContentModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, data: dict):
        self.panel_id = panel_id
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=2000, placeholder="Clique no botão abaixo para ser atendido por nossa equipe.", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
        ]
        super().__init__(title="Editar Estilo: Texto Simples", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        if self.panel_id in config.get("panels", {}):
            if "content" not in config["panels"][self.panel_id]:
                config["panels"][self.panel_id]["content"] = {}

            new_data = inter.text_values.copy()
            if "image_url" in new_data and not new_data["image_url"]:
                config["panels"][self.panel_id]["content"].pop("image_url", None)
                del new_data["image_url"]
            if "content" in new_data and not new_data["content"]:
                config["panels"][self.panel_id]["content"].pop("content", None)
                del new_data["content"]

            config["panels"][self.panel_id]["content"].update(new_data)
            config["panels"][self.panel_id]["has_pending_changes"] = True
            db.save_document("tickets_config", config)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter, self.panel_id))
        else:
            embed, components = MessageEditView_embed(inter, self.panel_id)
            await inter.response.edit_message(content=None, embed=embed, components=components)


class EditContainerModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, data: dict):
        self.panel_id = panel_id
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para ser atendido por nossa equipe.", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Estilo: Container", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        if self.panel_id in config.get("panels", {}):
            if "container" not in config["panels"][self.panel_id]:
                config["panels"][self.panel_id]["container"] = {}
            
            new_data = inter.text_values.copy()
            if "color" in new_data and not new_data["color"]:
                config["panels"][self.panel_id]["container"].pop("color", None)
                del new_data["color"]
            if "image_url" in new_data and not new_data["image_url"]:
                config["panels"][self.panel_id]["container"].pop("image_url", None)
                del new_data["image_url"]
            if "thumbnail_url" in new_data and not new_data["thumbnail_url"]:
                config["panels"][self.panel_id]["container"].pop("thumbnail_url", None)
                del new_data["thumbnail_url"]
            config["panels"][self.panel_id]["container"].pop("title", None)

            config["panels"][self.panel_id]["container"].update(new_data)
            config["panels"][self.panel_id]["has_pending_changes"] = True
            db.save_document("tickets_config", config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter, self.panel_id))
        else:
            embed, components = MessageEditView_embed(inter, self.panel_id)
            await inter.response.edit_message(content=None, embed=embed, components=components)


class EditTicketMessageModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, modal_config: dict, data: dict):
        self.panel_id = panel_id
        self.modal_config = modal_config
        self.message_keys = list(modal_config["fields"].keys())

        title = modal_config["title"]
        
        default_messages = {
            "close_message": "Olá {user_mention}, seu ticket `{channel_name}` em `{guild_name}` foi fechado por {autor_name} ({autor_mention}).",
            "close_message_reason": "Olá {user_mention}, seu ticket `{channel_name}` em `{guild_name}` foi fechado por {autor_name} ({autor_mention}).\n**Motivo:** {reason}",
            "notify_message_staff_to_user": "Olá {user_mention}, o atendente {autor_name} ({autor_mention}) está te notificando sobre o seu ticket `{channel_name}` em `{guild_name}`. A equipe de suporte está aguardando sua resposta.",
            "notify_message_user_to_staff": "{user_name} ({user_mention}) está solicitando a atenção de {atendente_name} ({attendant_mention}) no ticket `{channel_name}` em `{guild_name}`.",
            "add_user_message": "{alvo_mention} foi adicionado ao ticket `{channel_name}` em `{guild_name}` por {autor_name} ({autor_mention}).",
            "add_user_dm_message": "Olá {alvo_mention}, {autor_name} ({autor_mention}) te adicionou ao ticket `{channel_name}` em `{guild_name}`.",
            "remove_user_message": "{alvo_mention} foi removido do ticket `{channel_name}` em `{guild_name}` por {autor_name} ({autor_mention}).",
            "remove_user_dm_message": "Olá {alvo_mention}, {autor_name} ({autor_mention}) te removeu do ticket `{channel_name}` em `{guild_name}`.",
            "assume_message": "{autor_name} ({autor_mention}) assumiu o atendimento do ticket `{channel_name}` de {user_name} ({user_mention}) em `{guild_name}`.",
            "assume_dm_message": "Olá {user_mention}, o atendente {autor_name} ({autor_mention}) assumiu seu ticket `{channel_name}` em `{guild_name}`.",
            "transfer_message": "{autor_name} ({autor_mention}) transferiu o ticket de {old_owner_name} ({old_owner_mention}) para {new_owner_name} ({new_owner_mention}) no servidor `{guild_name}`.",
            "create_call_message": "Uma call de voz foi iniciada para o ticket `{channel_name}` de {user_name} ({user_mention}) em `{guild_name}` por {autor_name} ({autor_mention}).",
            "create_call_dm_message": "Olá {user_mention}! Uma call de voz foi criada para o seu ticket `{channel_name}` em `{guild_name}` por {autor_name} ({autor_mention}).",
            "request_call_message": "O usuário {user_name} ({user_mention}) solicitou a criação de uma call no ticket `{channel_name}` em `{guild_name}`.",
            "transcript_message": "Olá {user_mention}, aqui está o transcript do seu ticket `{channel_name}` no servidor `{guild_name}`.",
            "transcript_dm_message": "Olá {user_mention}, aqui está o transcript que você solicitou para o ticket `{channel_name}` no servidor `{guild_name}`."
        }

        components = []
        for key, field_data in modal_config["fields"].items():
            components.append(disnake.ui.TextInput(
                label=field_data["label"],
                custom_id=key,
                value=data.get(key, default_messages.get(key, "")),
                style=disnake.TextInputStyle.paragraph,
                max_length=2000,
                required=False
            ))

        super().__init__(title=title, components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        if self.panel_id in config.get("panels", {}):
            if "messages" not in config["panels"][self.panel_id]:
                config["panels"][self.panel_id]["messages"] = {}

            for key in self.message_keys:
                new_value = inter.text_values[key]
                if new_value:
                    config["panels"][self.panel_id]["messages"][key] = new_value
                else:
                    config["panels"][self.panel_id]["messages"].pop(key, None)

            db.save_document("tickets_config", config)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await message.wait(inter)
                await inter.edit_original_message(components=MessageEditSelectionView_components(inter, self.panel_id))
            else:
                await embed_message.wait(inter)
                embed, components = MessageEditSelectionView_embed(inter, self.panel_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.response.send_message("Painel não encontrado.", ephemeral=True)


# --- Views ---

def MessageEditSelectionView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > Editar Mensagem > **{panel_name}**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"TicketMsgEdit_SelectType_{panel_id}",
                    placeholder="Selecione qual mensagem editar",
                    options=[
                        disnake.SelectOption(label="Editar Mensagem do Painel", value="PanelMessage", emoji=emoji.message, description="Editar a mensagem do painel."),
                        disnake.SelectOption(label="Editar Mensagem de Abertura", value="OpenMessage", emoji=emoji.ticket, description="Editar a mensagem de abertura."),
                        disnake.SelectOption(label="Editar Mensagem de Fechamento", value="CloseMessage", emoji=emoji.delete, description="Editar a mensagem de fechamento."),
                        disnake.SelectOption(label="Editar Mensagem de Notificar", value="NotifyMessage", emoji=emoji.warn, description="Editar a mensagem da função de notificar."),
                        disnake.SelectOption(label="Editar Mensagem de Adicionar Usuário", value="AddUserMessage", emoji=emoji.plus, description="Editar a mensagem de adicionar usuário."),
                        disnake.SelectOption(label="Editar Mensagem de Remover Usuário", value="RemoveUserMessage", emoji=emoji.minus, description="Editar a mensagem de remover usuário."),
                        disnake.SelectOption(label="Editar Mensagem de Assumir", value="AssumeMessage", emoji=emoji.double_check, description="Editar a mensagem da função de assumir."),
                        disnake.SelectOption(label="Editar Mensagem de Transferir", value="TransferMessage", emoji=emoji.arrow, description="Editar a mensagem da função de transferir."),
                        disnake.SelectOption(label="Editar Mensagem de Criar Call", value="CreateCallMessage", emoji=emoji.voice, description="Editar a mensagem da função de criar call."),
                        disnake.SelectOption(label="Editar Mensagem de Transcript", value="TranscriptMessage", emoji=emoji.receipt, description="Editar a mensagem enviada com o transcript."),
                    ]
                )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}"),
        disnake.ui.Button(label="Prefixos", style=disnake.ButtonStyle.grey, emoji=emoji.information, custom_id=f"TicketMsgEdit_ShowPrefixes_{panel_id}"),
    )
    return [container, buttons]

def MessageEditSelectionView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editar Mensagem: {panel_name}",
        description="Selecione qual mensagem você deseja editar:",
        **embed_kwargs
    )
    # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    # embed.timestamp = disnake.utils.utcnow()
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"TicketMsgEdit_SelectType_{panel_id}",
                placeholder="Selecione qual mensagem editar",
                options=[
                    disnake.SelectOption(label="Editar Mensagem do Painel", value="PanelMessage", emoji=emoji.message, description="Editar a mensagem do painel."),
                    disnake.SelectOption(label="Editar Mensagem de Abertura", value="OpenMessage", emoji=emoji.ticket, description="Editar a mensagem de abertura."),
                    disnake.SelectOption(label="Editar Mensagem de Fechamento", value="CloseMessage", emoji=emoji.delete, description="Editar a mensagem de fechamento."),
                    disnake.SelectOption(label="Editar Mensagem de Notificar", value="NotifyMessage", emoji=emoji.warn, description="Editar a mensagem da função de notificar."),
                    disnake.SelectOption(label="Editar Mensagem de Adicionar Usuário", value="AddUserMessage", emoji=emoji.plus, description="Editar a mensagem de adicionar usuário."),
                    disnake.SelectOption(label="Editar Mensagem de Remover Usuário", value="RemoveUserMessage", emoji=emoji.minus, description="Editar a mensagem de remover usuário."),
                    disnake.SelectOption(label="Editar Mensagem de Assumir", value="AssumeMessage", emoji=emoji.double_check, description="Editar a mensagem da função de assumir."),
                    disnake.SelectOption(label="Editar Mensagem de Transferir", value="TransferMessage", emoji=emoji.arrow, description="Editar a mensagem da função de transferir."),
                    disnake.SelectOption(label="Editar Mensagem de Criar Call", value="CreateCallMessage", emoji=emoji.voice, description="Editar a mensagem da função de criar call."),
                    disnake.SelectOption(label="Editar Mensagem de Transcript", value="TranscriptMessage", emoji=emoji.receipt, description="Editar a mensagem enviada com o transcript."),
                ]
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}"),
            disnake.ui.Button(label="Prefixos", style=disnake.ButtonStyle.grey, emoji=emoji.information, custom_id=f"TicketMsgEdit_ShowPrefixes_{panel_id}"),
        )
    ]
    return embed, components

def MessageEditView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id)
    if not panel_data:
        from .edit_panel import EditPanelView_components
        return EditPanelView_components()

    primary_color_hex = db.get_document("custom_colors").get("primary")
    style = panel_data.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(panel_data.get("button", {}).get("label"))
    options_count = len(panel_data.get("options", []))
    
    content_configured = False
    if style == "embed":
        content_configured = bool(panel_data.get("embed", {}).get("title"))
    elif style == "content":
        content_data = panel_data.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(panel_data.get(style, {}).get("content"))
    
    preview_enabled = content_configured

    # Determinar status do botão
    if options_count > 1:
        button_status = "`Opcional (usa select)`"
        button_emoji_status = emoji.information
    elif button_configured:
        button_status = "`Configurado`"
        button_emoji_status = emoji.correct
    else:
        button_status = "`Padrão (cinza + 📧)`"
        button_emoji_status = emoji.information

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{button_emoji_status} **Botão:** {button_status}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    main_container_children = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > Editar Mensagem > **{panel_data.get('name')}**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id=f"TicketMsgEdit_CycleStyle_{panel_id}"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id=f"TicketMsgEdit_EditButton_{panel_id}"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"TicketMsgEdit_EditContent_{panel_id}"),
        ),
    ]

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(*main_container_children, **container_kwargs)
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_OpenMessageEditor_{panel_id}"),
        disnake.ui.Button(label="Preview", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id=f"TicketMsgEdit_Preview_{panel_id}", disabled=not preview_enabled)
    )

    return [container, buttons]

def MessageEditView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id)
    if not panel_data:
        from .edit_panel import EditPanelView_embed
        return EditPanelView_embed(inter)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    style = panel_data.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(panel_data.get("button", {}).get("label"))
    options_count = len(panel_data.get("options", []))
    
    content_configured = False
    if style == "embed":
        content_configured = bool(panel_data.get("embed", {}).get("title"))
    elif style == "content":
        content_data = panel_data.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(panel_data.get(style, {}).get("content"))
    
    preview_enabled = content_configured

    # Determinar status do botão
    if options_count > 1:
        button_status = "`Opcional (usa select)`"
        button_emoji_status = emoji.information
    elif button_configured:
        button_status = "`Configurado`"
        button_emoji_status = emoji.correct
    else:
        button_status = "`Padrão (cinza + 📧)`"
        button_emoji_status = emoji.information

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{button_emoji_status} **Botão:** {button_status}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editar Mensagem do Painel: {panel_data.get('name')}",
        description=status_text,
        **embed_kwargs
    )
    # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    # embed.timestamp = disnake.utils.utcnow()

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id=f"TicketMsgEdit_CycleStyle_{panel_id}"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id=f"TicketMsgEdit_EditButton_{panel_id}"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"TicketMsgEdit_EditContent_{panel_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_OpenMessageEditor_{panel_id}"),
            disnake.ui.Button(label="Preview", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id=f"TicketMsgEdit_Preview_{panel_id}", disabled=not preview_enabled)
        )
    ]

    return embed, components


# --- Message Preview Views ---

class MessagePreviewSelect(disnake.ui.StringSelect):
    def __init__(self, panel_id: str):
        self.panel_id = panel_id
        options = [
            disnake.SelectOption(label="Mensagem do Painel", value="PanelMessage", emoji=emoji.message, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Abertura", value="OpenMessage", emoji=emoji.ticket, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Fechamento", value="CloseMessage", emoji=emoji.delete, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Notificar", value="NotifyMessage", emoji=emoji.warn, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Adicionar Usuário", value="AddUserMessage", emoji=emoji.plus, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Remover Usuário", value="RemoveUserMessage", emoji=emoji.minus, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Assumir", value="AssumeMessage", emoji=emoji.double_check, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Transferir", value="TransferMessage", emoji=emoji.arrow, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Criar Call", value="CreateCallMessage", emoji=emoji.voice, description="Clique para visualizar."),
            disnake.SelectOption(label="Mensagem de Transcript", value="TranscriptMessage", emoji=emoji.receipt, description="Clique para visualizar."),
        ]
        super().__init__(
            placeholder="Selecione a categoria da mensagem...",
            custom_id=f"TicketMsgPreview_SelectCat_{panel_id}",
            options=options
        )

def MessagePreviewSelectionView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > Visualizar Mensagem > **{panel_name}**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(MessagePreviewSelect(panel_id)),
        **container_kwargs
    )
    
    return [container]

def MessagePreviewSelectionView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Visualizar Mensagem: {panel_name}",
        description="Selecione a categoria da mensagem que deseja visualizar:",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(MessagePreviewSelect(panel_id))
    ]
    
    return embed, components

class MessageSubtypePreviewSelect(disnake.ui.StringSelect):
    def __init__(self, panel_id: str, category: str, fields: dict):
        self.panel_id = panel_id
        options = [
            disnake.SelectOption(
                label=field_data["label"],
                value=key,
                description=field_data.get("description"),
                emoji=field_data.get("emoji")
            )
            for key, field_data in fields.items()
        ]

        super().__init__(
            placeholder="Selecione a mensagem específica...",
            custom_id=f"TicketMsgPreview_SelectSub_{panel_id}_{category}",
            options=options
        )

class MessageSubtypePreviewView(disnake.ui.View):
    def __init__(self, panel_id: str, category: str, fields: dict):
        super().__init__(timeout=180)
        self.add_item(MessageSubtypePreviewSelect(panel_id, category, fields))


async def show_prefixes_panel(inter: disnake.Interaction):
    prefixes_text = (
        "## Prefixos Disponíveis\n"
        "-# Use esses prefixos nas mensagens para personalizar o texto dinamicamente.\n\n"
        "**Usuário do Ticket**\n"
        "`{user_mention}` → <@123456789> *(menção do dono do ticket)*\n"
        "`{user_name}` → João *(nome do dono do ticket)*\n\n"
        "**Autor da Ação**\n"
        "`{autor_mention}` → <@987654321> *(menção de quem executou a ação)*\n"
        "`{autor_name}` → Carlos *(nome de quem executou a ação)*\n\n"
        "**Atendente**\n"
        "`{atendente_name}` → Ana *(nome do atendente assumido)*\n"
        "`{attendant_mention}` → <@111222333> *(menção do atendente assumido)*\n\n"
        "**Alvo (Adicionar/Remover Usuário)**\n"
        "`{alvo_mention}` → <@444555666> *(menção do usuário alvo)*\n\n"
        "**Transferência**\n"
        "`{old_owner_name}` → Pedro *(nome do dono anterior)*\n"
        "`{old_owner_mention}` → <@777888999> *(menção do dono anterior)*\n"
        "`{new_owner_name}` → Lucas *(nome do novo dono)*\n"
        "`{new_owner_mention}` → <@000111222> *(menção do novo dono)*\n\n"
        "**Ticket / Servidor**\n"
        "`{channel_name}` → ticket-joao-0042 *(nome do canal do ticket)*\n"
        "`{guild_name}` → Meu Servidor *(nome do servidor)*\n\n"
        "**Outros**\n"
        "`{reason}` → Problema resolvido *(motivo informado na ação)*\n"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    mode = db.get_document("custom_mode").get("mode")

    if mode == "components":
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(prefixes_text),
            **container_kwargs
        )
        await inter.response.send_message(components=[container], ephemeral=True)
    else:
        embed_kwargs = {}
        if primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(title="Prefixos Disponíveis", description=prefixes_text, **embed_kwargs)
        await inter.response.send_message(embed=embed, ephemeral=True)
