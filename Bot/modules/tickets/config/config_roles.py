import disnake
from functions.database import database as db
from functions.emoji import emoji

def get_option_data(panel_id: str, option_id: str) -> dict:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    options = panel_data.get("options", [])
    return next((opt for opt in options if str(opt.get("id")) == option_id), {})

def RolesOptionSelectView_components(inter: disnake.Interaction, panel_id: str) -> list:
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
        custom_id=f"TicketRoles_SelectOption_{panel_id}",
        placeholder="Selecione uma opção para configurar os cargos",
        options=select_options,
        disabled=not options
    )
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container_components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > {panel_name} > **Selecionar Opção**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]

    if not options:
        container_components.append(disnake.ui.TextDisplay("Este painel não possui opções de ticket. Crie opções em `Editar Opções` antes de configurar os cargos."))

    container_components.append(disnake.ui.ActionRow(select))
    
    container = disnake.ui.Container(
        *container_components,
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
    )
    
    return [container, buttons]

def RolesOptionSelectView_embed(inter: disnake.Interaction, panel_id: str):
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
        custom_id=f"TicketRoles_SelectOption_{panel_id}",
        placeholder="Selecione uma opção para configurar",
        options=select_options,
        disabled=not options
    )
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurar Cargos: {panel_name}",
        description="Este painel possui múltiplas opções de ticket. Selecione qual delas você deseja configurar os cargos.",
        **embed_kwargs
    )

    if not options:
        embed.description = "Este painel não possui opções de ticket. Crie opções em `Editar Opções` antes de configurar os cargos."
    
    components = [
        disnake.ui.ActionRow(select),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
        )
    ]
    return embed, components


def RolesConfigView_components(inter: disnake.Interaction, panel_id: str, option_id: str) -> list[disnake.ui.Container]:
    option_data = get_option_data(panel_id, option_id)
    option_name = option_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    roles_data = option_data.get("roles", {})
    
    def get_role_mentions(role_ids):
        mentions = [f"<@&{rid}>" for rid in role_ids]
        return ", ".join(mentions) if mentions else "`Nenhum`"

    atendentes_roles_str = get_role_mentions(roles_data.get("mention", []))
    allowed_roles_str = get_role_mentions(roles_data.get("allowed", []))
    forbidden_roles_str = get_role_mentions(roles_data.get("forbidden", []))

    roles_status = (
        f"{emoji.hammer} **Cargos de Atendentes:**\n{atendentes_roles_str}\n"
        f"{emoji.double_check} **Cargos Permitidos:**\n{allowed_roles_str}\n"
        f"{emoji.wrong} **Cargos Proibidos:**\n{forbidden_roles_str}\n"
    )

    is_anything_configured = any(roles_data.values())

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > **Editar Cargos ({option_name})**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(roles_status),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id=f"TicketRoles_Select_{panel_id}_{option_id}",
                    placeholder="Selecione uma opção para configurar",
                    options=[
                        disnake.SelectOption(label="Configurar cargos de atendentes", value="mention", emoji=emoji.hammer, description="Cargos dos atendentes do ticket."),
                        disnake.SelectOption(label="Configurar cargos permitidos", value="allowed", emoji=emoji.double_check, description="Cargos que podem abrir ticket no painel."),
                        disnake.SelectOption(label="Configurar cargos proibidos", value="forbidden", emoji=emoji.wrong, description="Cargos que não podem abrir ticket no painel."),
                    ]
                )
            ),
        **container_kwargs
    )
    
    # Define destino do botão Voltar: se há múltiplas opções, voltar para seleção de opção; caso contrário, voltar ao painel
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    options = panel_data.get("options", [])
    back_button_id = f"TicketRoles_BackToSelect_{panel_id}" if len(options) > 1 else f"TicketEdit_BackToPanel_{panel_id}"

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=back_button_id),
        disnake.ui.Button(label="Remover Tudo", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"TicketRoles_ClearAll_{panel_id}_{option_id}", disabled=not is_anything_configured)
    )
    
    return [container, buttons]

def RolesConfigView_embed(inter: disnake.Interaction, panel_id: str, option_id: str):
    option_data = get_option_data(panel_id, option_id)
    option_name = option_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    roles_data = option_data.get("roles", {})
    
    def get_role_mentions(role_ids):
        mentions = [f"<@&{rid}>" for rid in role_ids]
        return ", ".join(mentions) if mentions else "`Nenhum`"

    atendentes_roles_str = get_role_mentions(roles_data.get("mention", []))
    allowed_roles_str = get_role_mentions(roles_data.get("allowed", []))
    forbidden_roles_str = get_role_mentions(roles_data.get("forbidden", []))

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configuração de Cargos: {option_name}",
        **embed_kwargs
    )
    embed.add_field(name="Cargos de Atendentes:", value=atendentes_roles_str, inline=False)
    embed.add_field(name="Cargos Permitidos:", value=allowed_roles_str, inline=False)
    embed.add_field(name="Cargos Proibidos:", value=forbidden_roles_str, inline=False)

    is_anything_configured = any(roles_data.values())

    # Define destino do botão Voltar: se há múltiplas opções, voltar para seleção de opção; caso contrário, voltar ao painel
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    options = panel_data.get("options", [])
    back_button_id = f"TicketRoles_BackToSelect_{panel_id}" if len(options) > 1 else f"TicketEdit_BackToPanel_{panel_id}"

    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"TicketRoles_Select_{panel_id}_{option_id}",
                placeholder="Selecione uma opção para configurar",
                options=[
                    disnake.SelectOption(label="Configurar cargos de atendentes", value="mention", emoji=emoji.hammer, description="Cargos dos atendentes do ticket."),
                    disnake.SelectOption(label="Configurar cargos permitidos", value="allowed", emoji=emoji.double_check, description="Cargos que podem abrir ticket no painel."),
                    disnake.SelectOption(label="Configurar cargos proibidos", value="forbidden", emoji=emoji.wrong, description="Cargos que não podem abrir ticket no painel."),
                ]
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=back_button_id),
            disnake.ui.Button(label="Remover Tudo", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"TicketRoles_ClearAll_{panel_id}_{option_id}", disabled=not is_anything_configured)
        )
    ]
    return embed, components

def RoleSelectView_components(inter: disnake.Interaction, panel_id: str, option_id: str, role_type: str) -> list[disnake.ui.Container]:
    option_data = get_option_data(panel_id, option_id)
    option_name = option_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    type_map = {
        "mention": "Cargos de Atendentes",
        "allowed": "Cargos Permitidos",
        "forbidden": "Cargos Proibidos"
    }
    title = type_map.get(role_type, "Cargos")

    role_config = option_data.get("roles", {})
    selected_role_ids = role_config.get(role_type, [])
    
    def get_role_mentions(role_ids):
        mentions = [f"<@&{rid}>" for rid in role_ids]
        return ", ".join(mentions) if mentions else "`Nenhum`"

    selected_roles_str = get_role_mentions(selected_role_ids)

    main_container_components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > Editar Cargos > {option_name} > **{title}**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(f"**Cargos Atuais:** {selected_roles_str}"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]

    select = disnake.ui.RoleSelect(
        custom_id=f"TicketRoles_RoleSelect_{panel_id}_{option_id}_{role_type}",
        placeholder="Selecione os cargos",
        min_values=0,
        max_values=25,
    )
    main_container_components.append(disnake.ui.ActionRow(select))

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    main_container = disnake.ui.Container(*main_container_components, **container_kwargs)

    back_button_custom_id = f"TicketRoles_BackToConfig_{panel_id}_{option_id}"

    back_button_row = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=back_button_custom_id),
        disnake.ui.Button(label="Remover Tudo", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"TicketRoles_ClearType_{panel_id}_{option_id}_{role_type}", disabled=not selected_role_ids)
    )

    return [main_container, back_button_row]


def RoleSelectView_embed(inter: disnake.Interaction, panel_id: str, option_id: str, role_type: str):
    option_data = get_option_data(panel_id, option_id)
    option_name = option_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    type_map = {
        "mention": "Cargos de Atendentes",
        "allowed": "Cargos Permitidos",
        "forbidden": "Cargos Proibidos"
    }
    title = type_map.get(role_type, "Cargos")

    role_config = option_data.get("roles", {})
    selected_role_ids = role_config.get(role_type, [])
    
    def get_role_mentions(role_ids):
        mentions = [f"<@&{rid}>" for rid in role_ids]
        return ", ".join(mentions) if mentions else "`Nenhum`"

    selected_roles_str = get_role_mentions(selected_role_ids)

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editando: {title}",
        description=f"**Opção:** {option_name}\n**Cargos Atuais:** {selected_roles_str}",
        **embed_kwargs
    )

    select = disnake.ui.RoleSelect(
        custom_id=f"TicketRoles_RoleSelect_{panel_id}_{option_id}_{role_type}",
        placeholder="Selecione os cargos",
        min_values=0,
        max_values=25,
    )
    
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    
    back_button_custom_id = f"TicketRoles_BackToConfig_{panel_id}_{option_id}"

    components = [
        disnake.ui.ActionRow(select),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=back_button_custom_id),
            disnake.ui.Button(label="Remover Tudo", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"TicketRoles_ClearType_{panel_id}_{option_id}_{role_type}", disabled=not selected_role_ids)
        )
    ]
    return embed, components
