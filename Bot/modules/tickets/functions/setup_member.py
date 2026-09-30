import disnake
from functions.emoji import emoji

MEMBER_BUTTONS = {
    "close": {"label": "Fechar Ticket", "emoji": emoji.delete, "custom_id": "ticket_close_ticket_user", "row": 0, "description": "Permite que o membro feche o próprio ticket."},
    "notify": {"label": "Notificar Atendente", "emoji": emoji.warn, "custom_id": "ticket_notify_user", "row": 0, "description": "Envia uma notificação para a equipe de suporte."},
    "add_user": {"label": "Adicionar Usuário", "emoji": emoji.plus, "custom_id": "ticket_add_user_user", "row": 0, "description": "Permite que o membro adicione outros usuários ao ticket."},
    "remove_user": {"label": "Remover Usuário", "emoji": emoji.minus, "custom_id": "ticket_remove_user_user", "row": 0, "description": "Permite que o membro remova outros usuários do ticket."},
    "transfer": {"label": "Transferir", "emoji": emoji.arrow, "custom_id": "ticket_transfer_user", "row": 0, "description": "Permite que o membro transfira o ticket para outro usuário."},
    "request_call": {"label": "Solicitar Call", "emoji": emoji.voice, "custom_id": "ticket_request_call_user", "row": 1, "description": "Permite que o membro solicite uma chamada de voz."},
    "transcript": {"label": "Transcript", "emoji": emoji.receipt, "custom_id": "ticket_transcript_user", "row": 1, "description": "Permite que o membro salve um transcript da conversa."},
    #"rate": {"label": "Avaliar", "emoji": emoji.star, "custom_id": "ticket_review", "row": 1, "disabled": True, "description": "Permite que o membro avalie o atendimento recebido."},
    #"payment": {"label": "Pagamento", "emoji": emoji.wallet, "custom_id": "ticket_payment_user", "row": 1, "disabled": True, "description": "Permite que o membro crie um pagamento no ticket atual."}
}

class UserSetupView(disnake.ui.View):
    def __init__(self, panel_data: dict, option_data: dict | None = None):
        super().__init__(timeout=None)

        panel_preferences = panel_data.get("preferences", {}) or {}
        option_preferences = option_data.get("preferences", {}) if option_data else {}

        preferences = {**panel_preferences, **option_preferences}

        member_setup = preferences.get("member_setup") or {}
        disabled_buttons = member_setup.get("disabled_buttons") or []

        for key, data in MEMBER_BUTTONS.items():
            if key not in disabled_buttons:
                self.add_item(disnake.ui.Button(
                    label=data["label"],
                    style=disnake.ButtonStyle.grey,
                    emoji=data["emoji"],
                    custom_id=data["custom_id"],
                    row=data.get("row", 0),
                    disabled=data.get("disabled", False)
                ))
