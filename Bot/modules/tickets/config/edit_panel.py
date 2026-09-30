import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


def get_panels():
    config = db.get_document("tickets_config") or {}
    return config.get("panels", {})


class SelectPanelToEdit(disnake.ui.StringSelect):
    def __init__(self, panels_chunk: list[tuple[str, dict]], chunk_index: int, total_panels: int):
        options = [
            disnake.SelectOption(label=data["name"], value=panel_id, description=f"Clique para editar o painel")
            for panel_id, data in panels_chunk
        ]

        placeholder = "Selecione um painel para editar..."
        if total_panels > 25:
            start_index = chunk_index * 25 + 1
            end_index = start_index + len(panels_chunk) - 1
            placeholder = f"Selecione um painel... ({start_index}-{end_index})"

        if not options and total_panels == 0:
            options.append(disnake.SelectOption(label="Nenhum painel encontrado", value="disabled"))

        super().__init__(
            placeholder=placeholder,
            options=options,
            custom_id=f"select_panel_to_edit_{chunk_index}",
            disabled=(total_panels == 0)
        )


def EditPanelView_components() -> list[disnake.ui.Container]:
    panels = get_panels()
    panel_items = list(panels.items())
    num_panels = len(panel_items)
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerenciar Tickets > **Editar Painel**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small)
    ]

    if num_panels == 0:
        select = SelectPanelToEdit([], 0, 0)
        container_components.append(disnake.ui.ActionRow(select))
    else:
        chunk_size = 25
        for i in range(0, num_panels, chunk_size):
            chunk_index = i // chunk_size
            chunk = panel_items[i:i + chunk_size]
            select = SelectPanelToEdit(chunk, chunk_index, num_panels)
            container_components.append(disnake.ui.ActionRow(select))
            
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(*container_components, **container_kwargs)
    
    buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Ticket"),
        )
    
    return [container, buttons]

def EditPanelView_embed(inter: disnake.Interaction):
    panels = get_panels()
    panel_items = list(panels.items())
    num_panels = len(panel_items)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Editar Painel",
        description="Selecione um painel abaixo para editar suas configurações.",
        **embed_kwargs
    )
    # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    # embed.timestamp = disnake.utils.utcnow()

    components = []
    if num_panels == 0:
        select = SelectPanelToEdit([], 0, 0)
        components.append(disnake.ui.ActionRow(select))
    else:
        chunk_size = 25
        for i in range(0, num_panels, chunk_size):
            chunk_index = i // chunk_size
            chunk = panel_items[i:i + chunk_size]
            select = SelectPanelToEdit(chunk, chunk_index, num_panels)
            components.append(disnake.ui.ActionRow(select))

    components.append(disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Ticket"),
    ))

    return embed, components


def ChannelSelectView_components(panel_id: str) -> list[disnake.ui.Container]:
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerenciar Tickets > Editar Painel > **Editar Canal**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione um canal...",
                    custom_id=f"TicketEdit_SelectChannel_{panel_id}",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
    )
    
    return [container, buttons]

def ChannelSelectView_embed(inter: disnake.Interaction, panel_id: str):
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Editar Canal",
        description="Selecione o canal onde o painel de ticket será enviado.",
        **embed_kwargs
    )
    # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    # embed.timestamp = disnake.utils.utcnow()
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Selecione um canal...",
                custom_id=f"TicketEdit_SelectChannel_{panel_id}",
                channel_types=[disnake.ChannelType.text],
                min_values=1,
                max_values=1,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
        )
    ]

    return embed, components


def CategorySelectView_components(panel_id: str) -> list[disnake.ui.Container]:
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerenciar Tickets > Editar Painel > **Editar Categoria**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione uma categoria...",
                    custom_id=f"TicketEdit_SelectCategory_{panel_id}",
                    channel_types=[disnake.ChannelType.category],
                    min_values=1,
                    max_values=1,
                )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
    )

    return [container, buttons]

def CategorySelectView_embed(inter: disnake.Interaction, panel_id: str):
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editar Categoria",
        description="Selecione a categoria onde os tickets serão criados.",
        **embed_kwargs
    )
    # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    # embed.timestamp = disnake.utils.utcnow()
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Selecione uma categoria...",
                custom_id=f"TicketEdit_SelectCategory_{panel_id}",
                channel_types=[disnake.ChannelType.category],
                min_values=1,
                max_values=1,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
        )
    ]

    return embed, components


def SpecificPanelView_components(inter: disnake.Interaction, panel_id: str) -> list[disnake.ui.Container]:
    panels = get_panels()
    panel_data = panels.get(panel_id)
    if not panel_data:
        return EditPanelView_components()
        
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
    panel_name = panel_data.get('name', 'N/A')
    is_enabled = panel_data.get('enabled', False)
    channel_id = panel_data.get('channel_id')
    channel = inter.bot.get_channel(channel_id) if channel_id else None
    category_id = panel_data.get('category_id')
    category = inter.bot.get_channel(category_id) if category_id else None
    
    modes = {"channel": "`Canal`", "topic": "`Tópico`"}
    current_mode_key = panel_data.get("mode", "channel")
    mode_keys = list(modes.keys())
    current_mode_index = mode_keys.index(current_mode_key) if current_mode_key in mode_keys else 0
    current_mode_name = modes.get(current_mode_key, "N/A")

    office_hours_data = panel_data.get("office_hours", {})
    start_time = office_hours_data.get("start_time")
    end_time = office_hours_data.get("end_time")
    
    office_hours_display = f"{start_time} - {end_time}" if start_time and end_time else "Não configurado"
    office_hours_status = f"{emoji.clock} **Horário:** `{office_hours_display}`"
    
    ai_enabled = panel_data.get("ai_enabled", False)
    ai_status = f"{emoji.sparkles} **AmethysAi:** {'`Configurada`' if ai_enabled else '`Desativada`'}"

    auto_assume = panel_data.get("auto_assume_on_first_message", False)
    auto_assume_status = f"{emoji.on if auto_assume else emoji.off} **Assumir na primeira mensagem:** {'`Ativado`' if auto_assume else '`Desativado`'}"

    status_text = (
        f"{emoji.on if is_enabled else emoji.off} **Status:** {'`Ligado`' if is_enabled else '`Desligado`'}\n"
        f"{emoji.route} **Modo de Atendimento:** {current_mode_name}\n"
        f"{office_hours_status}\n"
        f"{ai_status}\n"
        f"{auto_assume_status}\n"
    )
    if current_mode_key == "channel":
        status_text += f"{emoji.dir if category else emoji.wrong} **Categoria:** `{category.name if category else 'Não Definida'}`\n"
    status_text += f"{emoji.textc if channel else emoji.wrong} **Canal:** {channel.mention if channel else 'Não Definido'}\n"

    toggle_button = disnake.ui.Button(
        label="",
        style=disnake.ButtonStyle.grey,
        emoji=emoji.power,
        custom_id=f"TicketEdit_ToggleEnable_{panel_id}"
    )

    auto_assume_button = disnake.ui.Button(
        #label="Assumir na primeira mensagem",
        style=disnake.ButtonStyle.green if auto_assume else disnake.ButtonStyle.grey,
        emoji=emoji.power if auto_assume else emoji.power,
        custom_id=f"TicketEdit_ToggleAutoAssume_{panel_id}",
        disabled=not is_enabled
    )
    
    message_id = panel_data.get("message_id")
    has_pending_changes = panel_data.get("has_pending_changes", True)
    
    style = panel_data.get("message_style", "embed")
    button_configured = bool(panel_data.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(panel_data.get("embed", {}).get("title"))
    elif style == "content":
        content_data = panel_data.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(panel_data.get(style, {}).get("content"))
    
    if not message_id:
        publish_button_label = "Enviar Painel"
    else:
        if has_pending_changes:
            publish_button_label = "Publicar Alterações"
        else:
            publish_button_label = "Enviar Painel"

    publish_button = disnake.ui.Button(
        label=publish_button_label,
        style=disnake.ButtonStyle.green,
        emoji=emoji.arrow,
        custom_id=f"TicketEdit_Sync_{panel_id}"
    )
    delete_button = disnake.ui.Button(label="Deletar Painel", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"TicketEdit_Delete_{panel_id}")

    mode_button_label = f"Alterar Modo ({current_mode_index + 1}/{len(modes)})"

    action_buttons = [
        toggle_button,
        auto_assume_button,
    ]
    if current_mode_key == "channel":
        action_buttons.append(
            disnake.ui.Button(label="Definir Categoria", style=disnake.ButtonStyle.blurple, emoji=emoji.dir, custom_id=f"TicketEdit_SetCategory_{panel_id}", disabled=not is_enabled)
        )
    action_buttons.append(
        disnake.ui.Button(label="Definir Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id=f"TicketEdit_SetChannel_{panel_id}", disabled=not is_enabled)
    )
    action_buttons.append(
        disnake.ui.Button(label="Editar Cargos", style=disnake.ButtonStyle.blurple, emoji=emoji.role, custom_id=f"TicketEdit_ConfigRoles_{panel_id}", disabled=not is_enabled)
    )
    preferences_button = disnake.ui.Button(label="Preferências", style=disnake.ButtonStyle.grey, emoji=emoji.settings2, custom_id=f"TicketEdit_Preferences_{panel_id}", disabled=not is_enabled)

    container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Gerenciar Tickets > Editar Painel > **{panel_name}**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(f"{status_text}"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Opções", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id=f"TicketEdit_EditOptions_{panel_id}", disabled=not is_enabled),
                disnake.ui.Button(label="Editar Mensagens", style=disnake.ButtonStyle.grey, emoji=emoji.message, custom_id=f"TicketEdit_OpenMessageEditor_{panel_id}", disabled=not is_enabled),
                disnake.ui.Button(label=mode_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.route, custom_id=f"TicketEdit_CycleMode_{panel_id}", disabled=not is_enabled),
            ),
             disnake.ui.ActionRow(
                disnake.ui.Button(label="Horário de Atendimento", style=disnake.ButtonStyle.grey, emoji=emoji.clock, custom_id=f"TicketEdit_Hours_{panel_id}", disabled=not is_enabled),
                disnake.ui.Button(label="AmethysAi", style=disnake.ButtonStyle.grey, emoji=emoji.sparkles, custom_id=f"TicketEdit_ConfigIA_{panel_id}", disabled=not is_enabled),
                preferences_button
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(*action_buttons),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Ticket_EditarPainel"),
        publish_button,
        delete_button
    )
    
    return [container, buttons]

def SpecificPanelView_embed(inter: disnake.Interaction, panel_id: str):
    panels = get_panels()
    panel_data = panels.get(panel_id)
    if not panel_data:
        return EditPanelView_embed(inter)
        
    primary_color_hex = db.get_document("custom_colors").get("primary")
    panel_name = panel_data.get('name', 'N/A')
    is_enabled = panel_data.get('enabled', False)
    channel_id = panel_data.get('channel_id')
    channel = inter.bot.get_channel(channel_id) if channel_id else None
    category_id = panel_data.get('category_id')
    category = inter.bot.get_channel(category_id) if category_id else None
    
    modes = {"channel": "`Canal`", "topic": "`Tópico`"}
    current_mode_key = panel_data.get("mode", "channel")
    mode_keys = list(modes.keys())
    current_mode_index = mode_keys.index(current_mode_key) if current_mode_key in mode_keys else 0
    current_mode_name = modes.get(current_mode_key, "N/A")

    mode_button_label = f"Alterar Modo ({current_mode_index + 1}/{len(modes)})"

    office_hours_data = panel_data.get("office_hours", {})
    start_time = office_hours_data.get("start_time")
    end_time = office_hours_data.get("end_time")
    
    office_hours_display = f"{start_time} - {end_time}" if start_time and end_time else "Não configurado"
    office_hours_status = f"{emoji.clock} **Horário:** `{office_hours_display}`"
    
    ai_enabled = panel_data.get("ai_enabled", False)
    ai_status = f"{emoji.sparkles} **AmethysAi:** {'`Configurada`' if ai_enabled else '`Desativada`'}"

    auto_assume = panel_data.get("auto_assume_on_first_message", False)
    auto_assume_status = f"{emoji.on if auto_assume else emoji.off} **Assumir na primeira mensagem:** {'`Ativado`' if auto_assume else '`Desativado`'}"

    status_text = (
        f"{emoji.on if is_enabled else emoji.off} **Status:** {'`Ligado`' if is_enabled else '`Desligado`'}\n"
        f"{emoji.route} **Modo de Atendimento:** {current_mode_name}\n"
        f"{office_hours_status}\n"
        f"{ai_status}\n"
        f"{auto_assume_status}\n"
    )
    if current_mode_key == "channel":
        status_text += f"{emoji.dir if category else emoji.wrong} **Categoria:** `{category.name if category else 'Não Definida'}`\n"
    status_text += f"{emoji.textc if channel else emoji.wrong} **Canal:** {channel.mention if channel else 'Não Definido'}\n"

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editando Painel: {panel_name}",
        **embed_kwargs
    )
    embed.add_field(name="Status e Configurações:\n\n", value=status_text, inline=False)
    # import datetime
    # embed.timestamp = datetime.datetime.utcnow()  # Força atualização visual
    
    # Cálculo de configuração dos botões e conteúdo
    style = panel_data.get("message_style", "embed")
    button_configured = bool(panel_data.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(panel_data.get("embed", {}).get("title"))
    elif style == "content":
        content_data = panel_data.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(panel_data.get(style, {}).get("content"))
        
    # Botões de publicar e deletar
    if not panel_data.get("message_id"):
        publish_button_label = "Enviar Painel"
    else:
        if panel_data.get("has_pending_changes", True):
            publish_button_label = "Publicar Alterações"
        else:
            publish_button_label = "Enviar Painel"
    publish_button = disnake.ui.Button(label=publish_button_label, style=disnake.ButtonStyle.green, emoji=emoji.arrow, custom_id=f"TicketEdit_Sync_{panel_id}")
    delete_button = disnake.ui.Button(label="Deletar Painel", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"TicketEdit_Delete_{panel_id}")

    toggle_button = disnake.ui.Button(
        label="",
        style=disnake.ButtonStyle.grey,
        emoji=emoji.power,
        custom_id=f"TicketEdit_ToggleEnable_{panel_id}"
    )
    auto_assume_button = disnake.ui.Button(
        label="Assumir na primeira mensagem",
        style=disnake.ButtonStyle.green if auto_assume else disnake.ButtonStyle.grey,
        emoji=emoji.on if auto_assume else emoji.off,
        custom_id=f"TicketEdit_ToggleAutoAssume_{panel_id}",
        disabled=not is_enabled
    )
    action_buttons = [
        toggle_button,
        auto_assume_button,
    ]
    if current_mode_key == "channel":
        action_buttons.append(
            disnake.ui.Button(label="Definir Categoria", style=disnake.ButtonStyle.blurple, emoji=emoji.dir, custom_id=f"TicketEdit_SetCategory_{panel_id}", disabled=not is_enabled)
        )
    action_buttons.append(
        disnake.ui.Button(label="Definir Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id=f"TicketEdit_SetChannel_{panel_id}", disabled=not is_enabled)
    )
    action_buttons.append(
        disnake.ui.Button(label="Editar Cargos", style=disnake.ButtonStyle.blurple, emoji=emoji.role, custom_id=f"TicketEdit_ConfigRoles_{panel_id}", disabled=not is_enabled)
    )

    components = []  # Inicializa corretamente

    # Garantir que cada custom_id é único por mensagem
    # Os botões são criados em ActionRows separados, cada um com custom_id único
    components.append(
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Editar Opções", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id=f"TicketEdit_EditOptions_{panel_id}", disabled=not is_enabled),
            disnake.ui.Button(label="Editar Mensagens", style=disnake.ButtonStyle.grey, emoji=emoji.message, custom_id=f"TicketEdit_OpenMessageEditor_{panel_id}", disabled=not is_enabled),
            disnake.ui.Button(label=mode_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.route, custom_id=f"TicketEdit_CycleMode_{panel_id}", disabled=not is_enabled),
        )
    )
    components.append(
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Horário de Atendimento", style=disnake.ButtonStyle.grey, emoji=emoji.clock, custom_id=f"TicketEdit_Hours_{panel_id}", disabled=not is_enabled),
            disnake.ui.Button(label="AmethysAi", style=disnake.ButtonStyle.grey, emoji=emoji.sparkles, custom_id=f"TicketEdit_ConfigIA_{panel_id}", disabled=not is_enabled),
            disnake.ui.Button(label="Preferências", style=disnake.ButtonStyle.grey, emoji=emoji.settings2, custom_id=f"TicketEdit_Preferences_{panel_id}", disabled=not is_enabled)
        )
    )
    components.append(
        disnake.ui.ActionRow(*action_buttons)
    )
    components.append(
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Ticket_EditarPainel"),
            publish_button,
            delete_button
        )
    )

    return embed, components
