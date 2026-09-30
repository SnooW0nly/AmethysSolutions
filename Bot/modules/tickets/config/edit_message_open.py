import disnake
from functions.database import database as db
from functions.emoji import emoji

def get_option_data(panel_id: str, option_id: str) -> dict:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    options = panel_data.get("options", [])
    return next((opt for opt in options if str(opt.get("id")) == option_id), {})

# --- Modals de Edição ---

class EditOpenEmbedModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, option_id: str, data: dict):
        self.panel_id = panel_id
        self.option_id = option_id
        components = [
            disnake.ui.TextInput(label="Título", custom_id="title", value=data.get("title"), max_length=256, placeholder="Seu ticket foi aberto!", required=True),
            disnake.ui.TextInput(label="Descrição", custom_id="description", value=data.get("description"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Aguarde um momento...", required=False),
            disnake.ui.TextInput(label="URL da Imagem/Banner", custom_id="image_url", value=data.get("image_url"), required=False),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Abertura: Embed", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        panels = config.get("panels", {})
        if self.panel_id in panels:
            options = panels[self.panel_id].get("options", [])
            for i, opt in enumerate(options):
                if str(opt.get("id")) == self.option_id:
                    open_message = panels[self.panel_id]["options"][i].setdefault("open_message", {})
                    open_message.setdefault("embed", {}).update(inter.text_values)
                    db.save_document("tickets_config", config)
                    break
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=OpenMessageEditView_components(inter, self.panel_id, self.option_id))
        else:
            embed, components = OpenMessageEditView_embed(inter, self.panel_id, self.option_id)
            await inter.response.edit_message(embed=embed, components=components)

class EditOpenContentModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, option_id: str, data: dict):
        self.panel_id = panel_id
        self.option_id = option_id
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=2000, required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False),
        ]
        super().__init__(title="Editar Abertura: Texto Simples", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        panels = config.get("panels", {})
        if self.panel_id in panels:
            options = panels[self.panel_id].get("options", [])
            for i, opt in enumerate(options):
                if str(opt.get("id")) == self.option_id:
                    open_message = panels[self.panel_id]["options"][i].setdefault("open_message", {})
                    open_message.setdefault("content", {}).update(inter.text_values)
                    db.save_document("tickets_config", config)
                    break

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=OpenMessageEditView_components(inter, self.panel_id, self.option_id))
        else:
            embed, components = OpenMessageEditView_embed(inter, self.panel_id, self.option_id)
            await inter.response.edit_message(embed=embed, components=components)


class EditOpenContainerModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, option_id: str, data: dict):
        self.panel_id = panel_id
        self.option_id = option_id
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Seu ticket foi aberto e em breve um atendente irá te auxiliar.", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Abertura: Container", components=components)
        
    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        panels = config.get("panels", {})
        if self.panel_id in panels:
            options = panels[self.panel_id].get("options", [])
            for i, opt in enumerate(options):
                if str(opt.get("id")) == self.option_id:
                    open_message = panels[self.panel_id]["options"][i].setdefault("open_message", {})
                    container = open_message.setdefault("container", {})
                    
                    new_data = inter.text_values
                    if "image_url" in new_data and not new_data["image_url"]:
                        container.pop("image_url", None)
                        del new_data["image_url"]
                    if "thumbnail_url" in new_data and not new_data["thumbnail_url"]:
                        container.pop("thumbnail_url", None)
                        del new_data["thumbnail_url"]

                    container.update(new_data)
                    db.save_document("tickets_config", config)
                    break

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=OpenMessageEditView_components(inter, self.panel_id, self.option_id))
        else:
            embed, components = OpenMessageEditView_embed(inter, self.panel_id, self.option_id)
            await inter.response.edit_message(embed=embed, components=components)

# --- Option Select View ---

def OpenMessageOptionSelectView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    options = panel_data.get("options", [])
    
    select_options = [
        disnake.SelectOption(
            label=opt.get("name", f"ID: {opt.get('id')}"),
            value=str(opt.get("id")),
            emoji=opt.get("emoji") or None,
            description=opt.get("description")
        ) for opt in options
    ]

    if not options:
        select_options.append(disnake.SelectOption(label="Nenhuma opção configurada", value="disabled"))

    select = disnake.ui.StringSelect(
        custom_id=f"TicketOpenMsg_SelectOption_{panel_id}",
        placeholder="Selecione uma opção para configurar a mensagem",
        options=select_options,
        disabled=not options
    )
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container_components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > {panel_name} > Editar Mensagem de Abertura > **Selecionar Opção**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]

    if not options:
        container_components.append(disnake.ui.TextDisplay("Este painel não possui opções de ticket. Crie opções em `Editar Opções` antes de configurar as mensagens."))

    container_components.append(disnake.ui.ActionRow(select))
    
    container = disnake.ui.Container(
        *container_components,
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_OpenMessageEditor_{panel_id}")
    )
    
    return [container, buttons]

def OpenMessageOptionSelectView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    options = panel_data.get("options", [])

    select_options = [
        disnake.SelectOption(
            label=opt.get("name", f"ID: {opt.get('id')}"),
            value=str(opt.get("id")),
            emoji=opt.get("emoji") or None,
            description=opt.get("description")
        ) for opt in options
    ]

    if not options:
        select_options.append(disnake.SelectOption(label="Nenhuma opção configurada", value="disabled"))

    select = disnake.ui.StringSelect(
        custom_id=f"TicketOpenMsg_SelectOption_{panel_id}",
        placeholder="Selecione uma opção para configurar",
        options=select_options,
        disabled=not options
    )
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurar Mensagem de Abertura: {panel_name}",
        description="Este painel possui múltiplas opções de ticket. Selecione qual delas você deseja configurar a mensagem de abertura.",
        **embed_kwargs
    )

    if not options:
        embed.description = "Este painel não possui opções de ticket. Crie opções em `Editar Opções` antes de configurar a mensagem."
    
    components = [
        disnake.ui.ActionRow(select),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_OpenMessageEditor_{panel_id}")
        )
    ]
    return embed, components

# --- View Principal ---

def OpenMessageEditView_components(inter: disnake.Interaction, panel_id: str, option_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')

    option_data = get_option_data(panel_id, option_id)
    option_name = option_data.get('name', 'N/A')
    open_message_data = option_data.get("open_message", {})
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    style = open_message_data.get("style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    content_configured = False
    if style == "embed":
        content_configured = bool(open_message_data.get("embed", {}).get("title") or open_message_data.get("embed", {}).get("description"))
    elif style == "content":
        content_configured = bool(open_message_data.get("content", {}).get("content") or open_message_data.get("content", {}).get("image_url"))
    elif style == "container":
        content_configured = bool(open_message_data.get("container", {}).get("content"))
        
    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    main_container_children = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > {panel_name} > {option_name} > **Editar Mensagem de Abertura**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id=f"TicketOpenMsgEdit_CycleStyle_{panel_id}_{option_id}"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"TicketOpenMsgEdit_EditContent_{panel_id}_{option_id}"),
        ),
    ]

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(*main_container_children, **container_kwargs)
    
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    
    back_button_custom_id = f"TicketOpenMsg_BackToSelect_{panel_id}"
    if len(panel_data.get("options", [])) <= 1:
        back_button_custom_id = f"TicketEdit_OpenMessageEditor_{panel_id}"

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=back_button_custom_id),
        disnake.ui.Button(label="Preview", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id=f"TicketOpenMsgEdit_Preview_{panel_id}_{option_id}", disabled=not content_configured)
    )

    return [container, buttons]


def OpenMessageEditView_embed(inter: disnake.Interaction, panel_id: str, option_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    
    option_data = get_option_data(panel_id, option_id)
    option_name = option_data.get('name', 'N/A')
    open_message_data = option_data.get("open_message", {})
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    style = open_message_data.get("style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    content_configured = False
    if style == "embed":
        content_configured = bool(open_message_data.get("embed", {}).get("title") or open_message_data.get("embed", {}).get("description"))
    elif style == "content":
        content_configured = bool(open_message_data.get("content", {}).get("content") or open_message_data.get("content", {}).get("image_url"))
    elif style == "container":
        content_configured = bool(open_message_data.get("container", {}).get("content"))
        
    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Abertura: {panel_name} > {option_name}",
        description=status_text,
        **embed_kwargs
    )
    # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    # embed.timestamp = disnake.utils.utcnow()

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id=f"TicketOpenMsgEdit_CycleStyle_{panel_id}_{option_id}"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"TicketOpenMsgEdit_EditContent_{panel_id}_{option_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketOpenMsg_BackToSelect_{panel_id}"),
            disnake.ui.Button(label="Preview", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id=f"TicketOpenMsgEdit_Preview_{panel_id}_{option_id}", disabled=not content_configured)
        )
    ]

    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    
    back_button_custom_id = f"TicketOpenMsg_BackToSelect_{panel_id}"
    if len(panel_data.get("options", [])) <= 1:
        back_button_custom_id = f"TicketEdit_OpenMessageEditor_{panel_id}"
        
    components[1].children[0].custom_id = back_button_custom_id

    return embed, components
