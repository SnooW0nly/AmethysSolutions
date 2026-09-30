import disnake
from functions.database import database as db
from functions.emoji import emoji

def get_giveaway_data(giveaway_id: str):
    config = db.obter("database/giveaways/giveaways_data.json")
    return config.get(giveaway_id, {})

def PreferencesView_components(inter: disnake.Interaction, giveaway_id: str) -> list[disnake.ui.Container]:
    giveaway_data = get_giveaway_data(giveaway_id)
    giveaway_name = giveaway_data.get("name", "N/A")
    giveaway_mode = giveaway_data.get("mode")
    monitor_enabled = giveaway_data.get("monitor_enabled", False)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    mode_text = "Real" if giveaway_mode == "real" else "Falso"
    monitor_status_text = "Ativo" if monitor_enabled else "Inativo"
    
    options = [
        disnake.SelectOption(label="Alterar modo do sorteio", value="change_mode", emoji=emoji.route, description="Alterne entre sorteio real ou falso."),
        disnake.SelectOption(label="Definir premiação", value="set_prize", emoji=emoji.gift, description="Defina a premiação do sorteio."),
        disnake.SelectOption(label="Definir cargos", value="set_roles", emoji=emoji.role, description="Configure os cargos do sorteio."),
        disnake.SelectOption(label="Definir requisitos", value="set_requirements", emoji=emoji.star, description="Configure as condições para participar."),
        disnake.SelectOption(label="Configurar monitor", value="config_monitor", emoji=emoji.cast, description="Configure o monitor do sorteio."),
    ]

    if giveaway_mode == "falso":
        options.insert(1, disnake.SelectOption(label="Definir ganhador", value="set_winner", emoji=emoji.member, description="Escolha o membros ou cargos que ganharão o sorteio."))

    select = disnake.ui.StringSelect(
        placeholder="Selecione uma opção para configurar...",
        options=options,
        custom_id=f"GiveawayPref_Select_{giveaway_id}"
    )

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > {giveaway_name} > **Preferências**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(f"{emoji.giveaway} **Modo de Sorteio Atual:** `{mode_text}`\n{emoji.cast} **Monitor:** `{monitor_status_text}`"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(select),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}")
    )

    return [container, buttons]

def PreferencesView_embed(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaway_data(giveaway_id)
    giveaway_name = giveaway_data.get("name", "N/A")
    giveaway_mode = giveaway_data.get("mode")
    monitor_enabled = giveaway_data.get("monitor_enabled", False)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Preferências: {giveaway_name}",
        **embed_kwargs
    )
    
    components = []

    mode_text = "Real" if giveaway_mode == "real" else "Falso"
    monitor_status_text = "Ativo" if monitor_enabled else "Inativo"
    embed.description = f"{emoji.giveaway} **Modo de Sorteio:** `{mode_text}`\n{emoji.cast} **Monitor:** `{monitor_status_text}`\n\nSelecione uma opção abaixo para configurar."

    options = [
        disnake.SelectOption(label="Alterar modo do sorteio", value="change_mode", emoji=emoji.route, description="Alterne entre sorteio real ou falso."),
        disnake.SelectOption(label="Definir premiação", value="set_prize", emoji=emoji.gift, description="Defina a premiação do sorteio."),
        disnake.SelectOption(label="Definir cargos", value="set_roles", emoji=emoji.role, description="Configure os cargos do sorteio."),
        disnake.SelectOption(label="Definir requisitos", value="set_requirements", emoji=emoji.star, description="Configure as condições para participar."),
        disnake.SelectOption(label="Configurar monitor", value="config_monitor", emoji=emoji.cast, description="Configure o monitor do sorteio."),
    ]

    if giveaway_mode == "falso":
        options.insert(1, disnake.SelectOption(label="Definir ganhador", value="set_winner", emoji=emoji.member, description="Escolha o membros ou cargos que ganharão o sorteio."))
    
    select = disnake.ui.StringSelect(
        placeholder="Selecione uma opção para configurar...",
        options=options,
        custom_id=f"GiveawayPref_Select_{giveaway_id}"
    )

    components.append(disnake.ui.ActionRow(select))

    components.append(disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}")
    ))

    return embed, components
