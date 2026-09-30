import disnake
from functions.database import database as db
from functions.emoji import emoji

def PreferenciasView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    options = [
        disnake.SelectOption(label="Configurar Sitema de Transcripts", value="Transcripts", emoji=emoji.receipt, description="Definir regras do sistema de transcripts."),
        disnake.SelectOption(label="Configurar Setup Membro", value="MemberSetup", emoji=emoji.members, description="Definir quais botões estarão disponíveis para o membro."),
        disnake.SelectOption(label="Configurar Setup Atendente", value="AttendantSetup", emoji=emoji.hammer, description="Definir quais botões estarão disponíveis para o atendente."),
        disnake.SelectOption(label="Configurar Fechamento de Tickets", value="CloseTickets", emoji=emoji.delete, description="Configurar o Fechamento de Tickets dos tickets."),
        disnake.SelectOption(label="Configurar Formulários", value="Forms", emoji=emoji.interrogation, description="Crie formulários para a abertura de tickets."),
        disnake.SelectOption(label="Configurar Suporte a Produto", value="ProductSupport", emoji=emoji.cardbox, description="Exibe as compras do usuário ao abrir um ticket.")
    ]

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > {panel_name} > **Preferências**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"TicketPreferences_Select_{panel_id}",
                placeholder="Selecione uma opção para configurar",
                options=options
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
    )
    return [container, buttons]

def PreferenciasView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    options = [
        disnake.SelectOption(label="Configurar Sitema de Transcripts", value="Transcripts", emoji=emoji.receipt, description="Definir regras do sistema de transcripts."),
        disnake.SelectOption(label="Configurar Setup Membro", value="MemberSetup", emoji=emoji.members, description="Definir quais botões estarão disponíveis para o membro."),
        disnake.SelectOption(label="Configurar Setup Atendente", value="AttendantSetup", emoji=emoji.hammer, description="Definir quais botões estarão disponíveis para o atendente."),
        disnake.SelectOption(label="Configurar Fechamento de Tickets", value="CloseTickets", emoji=emoji.delete, description="Configurar o Fechamento de Tickets dos tickets."),
        disnake.SelectOption(label="Configurar Formulários", value="Forms", emoji=emoji.interrogation, description="Crie formulários para a abertura de tickets."),
        disnake.SelectOption(label="Configurar Suporte a Produto", value="ProductSupport", emoji=emoji.cardbox, description="Exibe as compras do usuário ao abrir um ticket.")
    ]

    embed = disnake.Embed(
        title=f"Preferências: {panel_name}",
        description="Selecione uma das opções abaixo para configurar.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"TicketPreferences_Select_{panel_id}",
                placeholder="Selecione uma opção para configurar",
                options=options
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
        )
    ]
    return embed, components
