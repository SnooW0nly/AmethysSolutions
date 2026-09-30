import disnake
from functions.database import database as db
from functions.emoji import emoji
from modules.tickets.functions.setup_team import TEAM_BUTTONS

def TeamSetupView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    preferences = panel_data.get("preferences") or {}
    team_setup = preferences.get("team_setup") or {}
    disabled_buttons = team_setup.get("disabled_buttons") or []
    
    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    options = [
        disnake.SelectOption(label=data["label"], value=key, emoji=data.get("emoji"), description=data.get("description"), default=(key in disabled_buttons))
        for key, data in TEAM_BUTTONS.items()
    ]

    select_menu = disnake.ui.StringSelect(
        custom_id=f"TicketPref_TeamSetup_Select_{panel_id}",
        placeholder="Selecione os botões para desativar",
        options=options,
        min_values=0,
        max_values=len(options)
    )

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > {panel_name} > Preferências > **Setup do Atendente**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay("Selecione abaixo quais botões o atendente **NÃO** poderá ver no setup."),
        disnake.ui.ActionRow(select_menu),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
    )
    return [container, buttons]

def TeamSetupView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    preferences = panel_data.get("preferences") or {}
    team_setup = preferences.get("team_setup") or {}
    disabled_buttons = team_setup.get("disabled_buttons") or []

    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    options = [
        disnake.SelectOption(label=data["label"], value=key, emoji=data.get("emoji"), description=data.get("description"), default=(key in disabled_buttons))
        for key, data in TEAM_BUTTONS.items()
    ]
    
    select_menu = disnake.ui.StringSelect(
        custom_id=f"TicketPref_TeamSetup_Select_{panel_id}",
        placeholder="Selecione os botões para desativar",
        options=options,
        min_values=0,
        max_values=len(options)
    )

    embed = disnake.Embed(
        title=f"Preferências de Setup do Atendente: {panel_name}",
        description="Selecione abaixo quais botões o atendente **NÃO** poderá ver no setup.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(select_menu),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
        )
    ]
    return embed, components
