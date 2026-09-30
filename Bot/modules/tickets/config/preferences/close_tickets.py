import disnake
from functions.database import database as db
from functions.emoji import emoji

# --- Modals ---

class SetInactiveModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, data: dict):
        self.panel_id = panel_id
        components = [
            disnake.ui.TextInput(label="Tempo (em minutos)", custom_id="minutes", value=str(data.get("minutes", "0")), max_length=4, placeholder="0 = desativado", required=False),
            disnake.ui.TextInput(label="Mensagem de Aviso", custom_id="warn_message", value=data.get("warn_message", ""), style=disnake.TextInputStyle.paragraph, max_length=2000, required=False, placeholder="Deixe vazio para desativar"),
            disnake.ui.TextInput(label="Mensagem de Fechamento", custom_id="close_message", value=data.get("close_message", ""), style=disnake.TextInputStyle.paragraph, max_length=2000, required=False, placeholder="Deixe vazio para desativar"),
        ]
        super().__init__(title="Fechamento Auto por Inatividade", components=components, custom_id=f"SetInactiveModal_{self.panel_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # A lógica de salvar será no cog
        pass

class SetTimeCloseModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, data: dict):
        self.panel_id = panel_id
        components = [
            disnake.ui.TextInput(label="Horário (HH:MM)", custom_id="time", value=data.get("time", ""), max_length=5, placeholder="Deixe vazio para desativar", required=False),
            disnake.ui.TextInput(label="Mensagem de Fechamento", custom_id="close_message", value=data.get("close_message", ""), style=disnake.TextInputStyle.paragraph, max_length=2000, required=False, placeholder="Deixe vazio para desativar"),
        ]
        super().__init__(title="Fechamento em Horário Específico", components=components, custom_id=f"SetTimeCloseModal_{self.panel_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # A lógica de salvar será no cog
        pass

# --- Views ---

def CloseTicketsView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    preferences = panel_data.get("preferences", {}).get("auto_close", {})
    
    inactive = preferences.get("inactive", {})
    user_left = preferences.get("user_left", {})
    at_time = preferences.get("at_time", {})
    require_reason = panel_data.get("preferences", {}).get("require_reason", {})
    send_close_message = panel_data.get("preferences", {}).get("send_close_message", {})
    product_support = panel_data.get("preferences", {}).get("product_support", {})

    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    status_inactive = f"{emoji.on if inactive.get('enabled') else emoji.off} **Fechamento Auto por Inatividade**"
    status_user_left = f"{emoji.on if user_left.get('enabled') else emoji.off} **Fechamento Auto por Saída do Usuário**"
    status_at_time = f"{emoji.on if at_time.get('enabled') else emoji.off} **Fechamento Auto por Horário Específico**"
    status_require_reason = f"{emoji.on if require_reason.get('enabled') else emoji.off} **Exigir motivo para fechar o ticket**"
    status_send_close_message = f"{emoji.on if send_close_message.get('enabled', True) else emoji.off} **Enviar mensagem ao fechar ticket na DM**"
    status_product_support = f"{emoji.on if product_support.get('enabled') else emoji.off} **Suporte a Produto**"

    options = [
        disnake.SelectOption(label="Configurar Fechamento Auto por Inatividade", value="Inactive", emoji=emoji.clock, description="Fechar tickets após um período de inatividade."),
        disnake.SelectOption(label="Configurar Fechamento Auto por Saída do Usuário", value="UserLeft", emoji=emoji.member, description="Fechar tickets quando o usuário sair do servidor."),
        disnake.SelectOption(label="Configurar Fechamento Auto por Horário Específico", value="AtTime", emoji=emoji.calendar, description="Fechar tickets em um horário específico diariamente."),
        disnake.SelectOption(label="Configurar Motivo para Fechar o Ticket", value="RequireReason", emoji=emoji.textc, description="Um motivo deve ser inserido para fechar o ticket."),
        disnake.SelectOption(label="Configurar Mensagem de Fechamento na DM", value="SendCloseMessage", emoji=emoji.message, description="Controla o envio de uma DM ao fechar o ticket."),
        disnake.SelectOption(label="Ativar/Desativar Suporte a Produto", value="ProductSupport", emoji=emoji.cardbox, description="Exibe as compras do usuário ao abrir um ticket."),
    ]

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > {panel_name} > Preferências > **Fechamento de Tickets**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(f"{status_inactive}\n{status_user_left}\n{status_at_time}\n{status_require_reason}\n{status_send_close_message}\n{status_product_support}"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"TicketPref_CloseTickets_Select_{panel_id}",
                placeholder="Selecione uma opção para configurar",
                options=options
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
    )
    return [container, buttons]

def CloseTicketsView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    preferences = panel_data.get("preferences", {}).get("auto_close", {})

    inactive = preferences.get("inactive", {})
    user_left = preferences.get("user_left", {})
    at_time = preferences.get("at_time", {})
    require_reason = panel_data.get("preferences", {}).get("require_reason", {})
    send_close_message = panel_data.get("preferences", {}).get("send_close_message", {})
    product_support = panel_data.get("preferences", {}).get("product_support", {})

    panel_name = panel_data.get('name', 'N/A')
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    status_inactive = f"{emoji.on if inactive.get('enabled') else emoji.off} **Fechamento Auto por Inatividade**"
    status_user_left = f"{emoji.on if user_left.get('enabled') else emoji.off} **Fechamento Auto por Saída do Usuário**"
    status_at_time = f"{emoji.on if at_time.get('enabled') else emoji.off} **Fechamento Auto por Horário Específico**"
    status_require_reason = f"{emoji.on if require_reason.get('enabled') else emoji.off} **Exigir motivo para fechar o ticket**"
    status_send_close_message = f"{emoji.on if send_close_message.get('enabled', True) else emoji.off} **Enviar mensagem ao fechar ticket na DM**"
    status_product_support = f"{emoji.on if product_support.get('enabled') else emoji.off} **Suporte a Produto**"

    options = [
        disnake.SelectOption(label="Configurar Fechamento Auto por Inatividade", value="Inactive", emoji=emoji.clock, description="Fechar tickets após um período de inatividade."),
        disnake.SelectOption(label="Configurar Fechamento Auto por Saída do Usuário", value="UserLeft", emoji=emoji.member, description="Fechar tickets quando o usuário sair do servidor."),
        disnake.SelectOption(label="Configurar Fechamento Auto por Horário Específico", value="AtTime", emoji=emoji.calendar, description="Fechar tickets em um horário específico diariamente."),
        disnake.SelectOption(label="Configurar Motivo para Fechar o Ticket", value="RequireReason", emoji=emoji.textc, description="Um motivo deve ser inserido para fechar o ticket."),
        disnake.SelectOption(label="Configurar Mensagem de Fechamento na DM", value="SendCloseMessage", emoji=emoji.message, description="Controla o envio de uma DM ao fechar o ticket."),
        disnake.SelectOption(label="Ativar/Desativar Suporte a Produto", value="ProductSupport", emoji=emoji.cardbox, description="Exibe as compras do usuário ao abrir um ticket."),
    ]

    embed = disnake.Embed(
        title=f"Preferências de Fechamento de Tickets: {panel_name}",
        description=f"{status_inactive}\n{status_user_left}\n{status_at_time}\n{status_require_reason}\n{status_send_close_message}\n{status_product_support}",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"TicketPref_CloseTickets_Select_{panel_id}",
                placeholder="Selecione uma opção para configurar",
                options=options
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
        )
    ]
    return embed, components
