import disnake
from functions.database import database as db
from functions.emoji import emoji

def TranscriptsView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    preferences = panel_data.get("preferences", {}).get("transcripts", {})
    send_on_close = preferences.get("send_on_close", False)

    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    status_text = f"{emoji.on if send_on_close else emoji.off} **Status:** {'`Ativado`' if send_on_close else '`Desativado`'}"

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > {panel_name} > Preferências > **Transcripts**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay("Ao ativar, o transcript será enviado ao usuário ao fechar o ticket."),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="",
                emoji=emoji.power,
                style=disnake.ButtonStyle.grey,
                custom_id=f"TicketPref_Transcripts_Toggle_{panel_id}"
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
    )
    return [container, buttons]

def TranscriptsView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    preferences = panel_data.get("preferences", {}).get("transcripts", {})
    send_on_close = preferences.get("send_on_close", False)
    
    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    status_text = f"{emoji.on if send_on_close else emoji.off} **Status:** {'`Ativado`' if send_on_close else '`Desativado`'}"

    embed = disnake.Embed(
        title=f"Preferências de Transcripts: {panel_name}",
        description=f"{status_text}\nAo ativar, o transcript será enviado ao usuário ao fechar o ticket.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="",
                emoji=emoji.power,
                style=disnake.ButtonStyle.grey,
                custom_id=f"TicketPref_Transcripts_Toggle_{panel_id}"
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
        )
    ]
    return embed, components
