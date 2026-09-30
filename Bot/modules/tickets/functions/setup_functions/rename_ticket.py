import disnake
from disnake.ui import Modal, TextInput
from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms as perms_check
from ..history import log_ticket_event
from ..permissions import check_attendant_permissions, get_attendant_roles

class RenameTicketModal(Modal):
    def __init__(self, bot, channel: disnake.TextChannel | disnake.Thread):
        self.bot = bot
        self.channel = channel
        components = [
            TextInput(
                label="Novo nome do Ticket",
                placeholder="Digite o novo nome para o canal ou tópico.",
                custom_id="new_name",
                value=self.channel.name,
                max_length=100,
                required=True
            )
        ]
        super().__init__(title="Renomear Ticket", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        new_name = inter.text_values["new_name"]
        old_name = self.channel.name
        try:
            await self.channel.edit(name=new_name)
            
            log_ticket_event(
                self.channel.id,
                "rename",
                inter.author.id,
                {"old_name": old_name, "new_name": new_name}
            )
            
            await inter.response.send_message(f"O nome do ticket foi alterado para `{new_name}`.", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Ocorreu um erro ao tentar renomear o ticket: {e}", ephemeral=True)

async def rename_ticket(inter: disnake.MessageInteraction):
    # Verificar permissões
    has_permission = await check_attendant_permissions(inter.author, inter.channel.id)
    if not has_permission:
        return await inter.response.send_message(
            f"{emoji.wrong} Você não tem permissão para usar este comando.",
            ephemeral=True
        )
    
    config = db.get_document("tickets_config") or {}
    tickets_data = db.get_document("tickets_data") or {}

    found_panel_id = None
    for panel_id, users in tickets_data.get("panels", {}).items():
        for user_id, tickets in users.items():
            for ticket in tickets:
                if ticket.get("ticket_id") == inter.channel.id:
                    found_panel_id = panel_id
                    break
            if found_panel_id: break
        if found_panel_id: break
    
    if not found_panel_id:
        return await inter.response.send_message("Não foi possível encontrar a configuração para este ticket.", ephemeral=True)

    panel_data = config.get("panels", {}).get(found_panel_id, {})
    roles_data = panel_data.get("roles", {})
    atendentes_roles_ids = get_attendant_roles(roles_data)
    user_roles_ids = [role.id for role in inter.author.roles]
    is_atendente = any(role_id in atendentes_roles_ids for role_id in user_roles_ids)
    is_bot_admin = await perms_check.check(inter.author.id)

    if not is_atendente and not is_bot_admin:
        return await inter.response.send_message("Você não tem permissão para renomear este ticket.", ephemeral=True)

    await inter.response.send_modal(RenameTicketModal(inter.bot, inter.channel))
