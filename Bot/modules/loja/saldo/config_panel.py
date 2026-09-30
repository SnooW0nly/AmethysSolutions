"""
Painel de Configuração do Sistema de Saldo
"""
import disnake
from functions.database import database as db
from functions.emoji import emoji


def _format_bonus(config: dict) -> str:
    """Formata o bônus para exibição"""
    bonus = config.get("bonus", {})
    bonus_type = bonus.get("type", "disabled")
    bonus_value = bonus.get("value", 0)
    
    if bonus_type == "disabled":
        return "Desativado"
    elif bonus_type == "percentage":
        return f"{bonus_value}%"
    elif bonus_type == "fixed":
        return f"R$ {bonus_value:.2f}"
    return "Desativado"


def _format_rules(config: dict) -> str:
    """Formata as regras de saldo para exibição"""
    deposit_settings = config.get("deposit_settings", {})
    terms = deposit_settings.get("terms")
    
    if terms:
        return terms
    
    return "Não configurado"


def _format_deposit_settings(config: dict) -> str:
    """Formata as configurações de depósito"""
    settings = config.get("deposit_settings", {})
    
    min_dep = settings.get("min_deposit", 5.00)
    max_dep = settings.get("max_deposit", 1000.00)
    
    return f"R$ {min_dep:.2f} - R$ {max_dep:.2f}"


def panel_components(inter: disnake.MessageInteraction, config: dict) -> dict:
    """Retorna o painel no modo container v2"""
    color_data = db.get_document("custom_colors")
    primary_color_hex = color_data.get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
    
    is_enabled = config.get("enabled", False)
    status_text = f"Ligado" if is_enabled else "Desligado"
    toggle_label = "Desligar" if is_enabled else "Ligar"
    
    # Informações do sistema
    bonus_text = _format_bonus(config)
    rules_text = _format_rules(config)
    deposit_range = _format_deposit_settings(config)
    
    info_text = (
        f"{emoji.on if is_enabled else emoji.off} **Status:** `{status_text}`\n"
        f"{emoji.gift2} **Bônus:** `{bonus_text}`\n"
        f"{emoji.wallet} **Faixa de Depósito:** `{deposit_range}`"
    )
    
    # Botões
    toggle_button = disnake.ui.Button(
        label=toggle_label,
        emoji=emoji.power,
        style=disnake.ButtonStyle.success if not is_enabled else disnake.ButtonStyle.danger,
        custom_id="Saldo_Toggle"
    )
    
    bonus_button = disnake.ui.Button(
        label="Definir Bônus",
        emoji=emoji.gift2,
        style=disnake.ButtonStyle.secondary,
        custom_id="Saldo_Bonus"
    )
    
    rules_button = disnake.ui.Button(
        label="Definir Regras",
        emoji=emoji.settings2,
        style=disnake.ButtonStyle.secondary,
        custom_id="Saldo_Rules"
    )
    
    deposit_button = disnake.ui.Button(
        label="Painel de Depósito",
        emoji=emoji.wallet,
        style=disnake.ButtonStyle.primary,
        custom_id="Saldo_DepositPanel"
    )
    
    options_button = disnake.ui.Button(
        label="Opções",
        emoji=emoji.settings if hasattr(emoji, "settings") else emoji.settings2,
        style=disnake.ButtonStyle.grey,
        custom_id="Saldo_Options"
    )
    
    back_button = disnake.ui.Button(
        label="Voltar",
        emoji=emoji.back,
        style=disnake.ButtonStyle.grey,
        custom_id="Loja_Panel"
    )
    
    return {"components": [
        disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > **Sistema de Saldo**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info_text),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(toggle_button, bonus_button, rules_button),
            **container_kwargs
        ),
        disnake.ui.ActionRow(back_button, deposit_button, options_button),
    ]}


def panel_embed(inter: disnake.MessageInteraction, config: dict) -> dict:
    """Retorna o painel no modo embed"""
    color_data = db.get_document("custom_colors")
    primary_color_hex = color_data.get("primary")
    
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
    
    is_enabled = config.get("enabled", False)
    status_text = f"{emoji.correct} Ligado" if is_enabled else f"{emoji.wrong} Desligado"
    toggle_label = "Desligar" if is_enabled else "Ligar"
    
    # Informações do sistema
    bonus_text = _format_bonus(config)
    rules_text = _format_rules(config)
    deposit_range = _format_deposit_settings(config)
    
    embed = disnake.Embed(
        title=f"Sistema de Saldo",
        description="-# Painel > Loja > **Sistema de Saldo**\n\nConfigure o sistema de saldo para sua loja.",
        **embed_kwargs
    )
    
    embed.add_field(name=f"{emoji.on if is_enabled else emoji.off} Status", value=status_text, inline=True)
    embed.add_field(name=f"{emoji.gift2} Bônus", value=f"`{bonus_text}`", inline=True)
    embed.add_field(name=f"{emoji.wallet} Faixa de Depósito", value=f"`{deposit_range}`", inline=True)
    
    # Botões
    toggle_button = disnake.ui.Button(
        label=toggle_label,
        emoji=emoji.power,
        style=disnake.ButtonStyle.success if not is_enabled else disnake.ButtonStyle.danger,
        custom_id="Saldo_Toggle"
    )
    
    bonus_button = disnake.ui.Button(
        label="Definir Bônus",
        emoji=emoji.gift2,
        style=disnake.ButtonStyle.secondary,
        custom_id="Saldo_Bonus"
    )
    
    rules_button = disnake.ui.Button(
        label="Definir Regras",
        emoji=emoji.settings2,
        style=disnake.ButtonStyle.secondary,
        custom_id="Saldo_Rules"
    )
    
    deposit_button = disnake.ui.Button(
        label="Painel de Depósito",
        emoji=emoji.wallet,
        style=disnake.ButtonStyle.primary,
        custom_id="Saldo_DepositPanel"
    )
    
    options_button = disnake.ui.Button(
        label="Opções",
        emoji=emoji.settings if hasattr(emoji, "settings") else emoji.settings2,
        style=disnake.ButtonStyle.grey,
        custom_id="Saldo_Options"
    )
    
    back_button = disnake.ui.Button(
        label="Voltar",
        emoji=emoji.back,
        style=disnake.ButtonStyle.grey,
        custom_id="Loja_Panel"
    )
    
    components = [
        disnake.ui.ActionRow(toggle_button, bonus_button, rules_button),
        disnake.ui.ActionRow(deposit_button, options_button),
        disnake.ui.ActionRow(back_button),
    ]
    
    return {"embed": embed, "components": components}
