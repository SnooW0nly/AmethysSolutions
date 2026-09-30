import disnake
from functions.database import database as db
from functions.emoji import emoji

def get_definicoes_data():
    cloud_data = db.get_document("cloud_data") or {}
    return cloud_data.get("definitions", {})

def DefinicoesView_components(inter: disnake.Interaction) -> list:
    data = get_definicoes_data()

    settings = {
        "remove_autorole": {
            "label": "Remover cargo de autorole ao se verificar",
            "description": "Remove o cargo de autorole do membro após a verificação bem-sucedida."
        },
        "sync_oauth2": {
            "label": "Sincronizar Verificação OAuth2",
            "description": "Sincroniza os dados do usuário com o servidor através da verificação OAuth2."
        },
        "require_oauth2": {
            "label": "Requerer Verificação OAuth2",
            "description": "Exige que os novos membros se verifiquem usando o fluxo OAuth2 para obter acesso."
        },
        "persistent_oauth2": {
            "label": "Verificação Persistente OAuth2",
            "description": "Mantém a verificação de um membro mesmo que ele saia e entre novamente no servidor."
        },
        "auto_join_oauth2": {
            "label": "Auto Join OAuth2",
            "description": "Adiciona o usuário automaticamente ao servidor após a conclusão da verificação OAuth2."
        },
        "block_vpn": {
            "label": "Bloquear uso de VPN na verificação",
            "description": "Impede que usuários utilizando VPN ou proxy concluam a verificação."
        },
        "block_mobile": {
            "label": "Bloquear o uso de 3/4/5G (Redes Móveis) na verificação",
            "description": "Bloqueia a verificação de usuários conectados a redes de dados móveis (3G/4G/5G)."
        },
        "block_no_verified_email": {
            "label": "Bloquear contas sem e-mail verificado na verificação",
            "description": "Impede a verificação de contas do Discord que não possuem um e-mail verificado."
        },
        "block_no_email": {
            "label": "Bloquear contas sem e-mail vinculado na verificação",
            "description": "Impede a verificação de contas do Discord que não possuem um e-mail vinculado."
        },
        "block_spam": {
            "label": "Bloquear contas de spam na verificação",
            "description": "Utiliza sistemas de detecção para bloquear contas de spam conhecidas durante a verificação."
        }
    }

    status_lines = []
    for key, value in settings.items():
        status = data.get(key, {}).get("enabled", False)
        status_lines.append(f"{emoji.on if status else emoji.off} **{value['label']}**")
    
    status_text = "\n".join(status_lines)

    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#7289da")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    options = [
        disnake.SelectOption(
            label=value['label'],
            value=key,
            emoji=emoji.power,
            description=value['description']
        ) for key, value in settings.items()
    ]

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Preferências**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id="CloudDefinicoes_Select",
                placeholder="Selecione uma opção para configurar",
                options=options
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_Back")
    )
    return [container, buttons]

def DefinicoesView_embed(inter: disnake.Interaction):
    data = get_definicoes_data()

    settings = {
        "remove_autorole": {
            "label": "Remover cargo de autorole ao se verificar",
            "description": "Remove o cargo de autorole do membro após a verificação bem-sucedida."
        },
        "sync_oauth2": {
            "label": "Sincronizar Verificação OAuth2",
            "description": "Sincroniza os dados do usuário com o servidor através da verificação OAuth2."
        },
        "require_oauth2": {
            "label": "Requerer Verificação OAuth2",
            "description": "Exige que os novos membros se verifiquem usando o fluxo OAuth2 para obter acesso."
        },
        "persistent_oauth2": {
            "label": "Verificação Persistente OAuth2",
            "description": "Mantém a verificação de um membro mesmo que ele saia e entre novamente no servidor."
        },
        "auto_join_oauth2": {
            "label": "Auto Join OAuth2",
            "description": "Adiciona o usuário automaticamente ao servidor após a conclusão da verificação OAuth2."
        },
        "block_vpn": {
            "label": "Bloquear uso de VPN na verificação",
            "description": "Impede que usuários utilizando VPN ou proxy concluam a verificação."
        },
        "block_mobile": {
            "label": "Bloquear o uso de 3/4/5G (Redes Móveis) na verificação",
            "description": "Bloqueia a verificação de usuários conectados a redes de dados móveis (3G/4G/5G)."
        },
        "block_no_verified_email": {
            "label": "Bloquear contas sem e-mail verificado na verificação",
            "description": "Impede a verificação de contas do Discord que não possuem um e-mail verificado."
        },
        "block_no_email": {
            "label": "Bloquear contas sem e-mail vinculado na verificação",
            "description": "Impede a verificação de contas do Discord que não possuem um e-mail vinculado."
        },
        "block_spam": {
            "label": "Bloquear contas de spam na verificação",
            "description": "Utiliza sistemas de detecção para bloquear contas de spam conhecidas durante a verificação."
        }
    }
    
    status_lines = []
    for key, value in settings.items():
        status = data.get(key, {}).get("enabled", False)
        status_lines.append(f"{emoji.on if status else emoji.off} **{value['label']}**")
    
    description = "\n".join(status_lines)
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#7289da")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Preferencias AmyCloud",
        description=description,
        **embed_kwargs
    )

    options = [
        disnake.SelectOption(
            label=value['label'],
            value=key,
            emoji=emoji.power,
            description=value['description']
        ) for key, value in settings.items()
    ]

    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id="CloudDefinicoes_Select",
                placeholder="Selecione uma opção para configurar",
                options=options
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_Back")
        )
    ]
    
    return embed, components
