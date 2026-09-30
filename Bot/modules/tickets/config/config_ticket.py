import disnake
from functions.emoji import emoji
from functions.database import database as db
from functions.utils import utils

def PainelTicket_components(inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
    config = db.get_document("tickets_config") or {}
    panels = config.get("panels", {})
    panel_count = len(panels)
    
    any_panel_enabled = any(p.get("enabled", False) for p in panels.values())

    toggle_all_button = disnake.ui.Button(
        label="Desligar Todos" if any_panel_enabled else "Ligar Todos",
        style=disnake.ButtonStyle.red if any_panel_enabled else disnake.ButtonStyle.green,
        emoji=emoji.power,
        custom_id="Ticket_ToggleAllPanels",
        disabled=panel_count == 0
    )
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > **Gerenciar Tickets**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(f"{emoji.receipt} **Paineis configurados:** `{panel_count}`"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            *[
                toggle_all_button for _ in range(1) if panel_count > 0
            ],
            disnake.ui.Button(label="Criar Painel", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Ticket_CriarPainel"),
            disnake.ui.Button(label="Editar Painel", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Ticket_EditarPainel", disabled=panel_count == 0),
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PainelInicial"),
    )
    
    return [container, buttons]

def PainelTicket_embed(inter: disnake.MessageInteraction):
    config = db.get_document("tickets_config") or {}
    panels = config.get("panels", {})
    panel_count = len(panels)
    
    any_panel_enabled = any(p.get("enabled", False) for p in panels.values())

    toggle_all_button = disnake.ui.Button(
        label="Desligar Todos" if any_panel_enabled else "Ligar Todos",
        style=disnake.ButtonStyle.red if any_panel_enabled else disnake.ButtonStyle.green,
        emoji=emoji.power,
        custom_id="Ticket_ToggleAllPanels",
        disabled=panel_count == 0
    )
    
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Gerenciar Tickets",
        description=f"{emoji.receipt} **Paineis configurados:** `{panel_count}`",
        **embed_kwargs
    )
    # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    # embed.timestamp = disnake.utils.utcnow()

    action_row_buttons = []
    if panel_count > 0:
        action_row_buttons.append(toggle_all_button)
    
    action_row_buttons.extend([
        disnake.ui.Button(label="Criar Painel", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Ticket_CriarPainel"),
        disnake.ui.Button(label="Editar Painel", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Ticket_EditarPainel", disabled=panel_count == 0),
    ])

    components = [
        disnake.ui.ActionRow(*action_row_buttons),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PainelInicial"),
        ),
    ]
    return embed, components
