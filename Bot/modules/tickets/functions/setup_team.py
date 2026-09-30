import disnake
from functions.emoji import emoji

TEAM_BUTTONS = {
    "close": {"label": "Fechar Ticket", "emoji": emoji.delete, "custom_id": "ticket_close_ticket", "description": "Permite que a equipe feche o ticket de um membro."},
    "assume": {"label": "Assumir Ticket", "emoji": emoji.double_check, "custom_id": "ticket_claim", "description": "Permite que um atendente assuma o ticket."},
    "notify": {"label": "Notificar Usuário", "emoji": emoji.warn, "custom_id": "ticket_notify", "description": "Envia uma notificação para o membro do ticket."},
    "rename": {"label": "Renomear Ticket", "emoji": emoji.edit, "custom_id": "ticket_rename", "description": "Permite que a equipe altere o nome do ticket."},
    "priority": {"label": "Definir Prioridade", "emoji": emoji.coupon, "custom_id": "ticket_set_priority", "description": "Permite que a equipe defina a prioridade do ticket."},
    "resolved": {"label": "Resolvido", "emoji": emoji.like, "custom_id": "ticket_resolved", "description": "Permite marcar o ticket como resolvido, sem fechá-lo."},
    "archive": {"label": "Arquivar Ticket", "emoji": emoji.dir, "custom_id": "ticket_archive", "description": "Permite que a equipe arquive o ticket atual."},
    "add_user": {"label": "Adicionar Usuário", "emoji": emoji.plus, "custom_id": "ticket_add_user", "description": "Permite que a equipe adicione outros usuários ao ticket."},
    "remove_user": {"label": "Remover Usuário", "emoji": emoji.minus, "custom_id": "ticket_remove_user", "description": "Permite que a equipe remova usuários do ticket."},
    "transcript": {"label": "Transcript", "emoji": emoji.receipt, "custom_id": "ticket_transcript", "description": "Permite que a equipe salve um transcript da conversa."},
    "history": {"label": "Histórico", "emoji": emoji.clock, "custom_id": "ticket_history", "description": "Exibe o histórico de usuários nos tickets do servidor."},
    "manage_call": {"label": "Gerênciar Call", "emoji": emoji.voice, "custom_id": "ticket_create_call", "description": "Inicia ou gerencia uma chamada de voz no ticket."},
    "transfer": {"label": "Transferir", "emoji": emoji.arrow, "custom_id": "ticket_transfer", "description": "Permite que a equipe transfira o ticket para outro usuário."},
    #"payment": {"label": "Pagamento", "emoji": emoji.wallet, "custom_id": "ticket_payment", "disabled": True, "description": "Permite que a equipe crie um pagamento no ticket atual."},
}

class AttendantSetupView(disnake.ui.View):
    def __init__(self, panel_data: dict, option_data: dict | None = None):
        super().__init__(timeout=None)
        
        panel_preferences = panel_data.get("preferences", {}) or {}
        option_preferences = option_data.get("preferences", {}) if option_data else {}
        
        preferences = {**panel_preferences, **option_preferences}

        team_setup = preferences.get("team_setup") or {}
        disabled_buttons = team_setup.get("disabled_buttons") or []

        for key, data in TEAM_BUTTONS.items():
            if key not in disabled_buttons:
                self.add_item(disnake.ui.Button(
                    label=data["label"],
                    style=disnake.ButtonStyle.grey,
                    emoji=data["emoji"],
                    custom_id=data["custom_id"],
                    disabled=data.get("disabled", False)
                ))
