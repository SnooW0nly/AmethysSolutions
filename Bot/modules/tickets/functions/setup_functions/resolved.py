import disnake
import re
from functions.database import database as db
from functions.perms import perms as perms_check
from ..history import log_ticket_event
from functions.emoji import emoji
from ..permissions import get_attendant_roles

async def resolved_ticket(inter: disnake.MessageInteraction | disnake.ApplicationCommandInteraction):
    config = db.get_document("tickets_config") or {}
    tickets_data = db.get_document("tickets_data") or {}

    ticket_info = None
    panel_id_found = None
    user_id_found = None

    for panel_id, users in tickets_data.get("panels", {}).items():
        if ticket_info: break
        for user_id, tickets in users.items():
            if ticket_info: break
            for ticket in tickets:
                if ticket.get("ticket_id") == inter.channel.id:
                    ticket_info = ticket
                    panel_id_found = panel_id
                    user_id_found = user_id
                    break
    
    if not ticket_info:
        return await inter.response.send_message("Não foi possível encontrar a configuração para este ticket.", ephemeral=True)

    if ticket_info.get("is_resolved"):
        return await inter.response.send_message(f"{emoji.warn} Este ticket já foi marcado como resolvido.", ephemeral=True)

    panel_data = config.get("panels", {}).get(panel_id_found, {})
    roles_data = panel_data.get("roles", {})
    atendentes_roles_ids = get_attendant_roles(roles_data)
    user_roles_ids = [role.id for role in inter.author.roles]
    is_atendente = any(role_id in atendentes_roles_ids for role_id in user_roles_ids)
    is_bot_admin = await perms_check.check(inter.author.id)

    if not is_atendente and not is_bot_admin:
        return await inter.response.send_message("Você não tem permissão para marcar este ticket como resolvido.", ephemeral=True)

    ticket_owner = await inter.bot.get_or_fetch_user(user_id_found)

    if not ticket_owner:
        return await inter.response.send_message("Não foi possível encontrar o autor do ticket.", ephemeral=True)

    await inter.response.defer(ephemeral=True)
    
    old_name = inter.channel.name
    
    # Sanitize username to be channel-name-safe and prevent errors
    sanitized_name = re.sub(r'[^\w-]', '', ticket_owner.name.lower())
    if not sanitized_name:
        sanitized_name = "user" # Fallback for names with only special characters
    new_name = f"✅┃resolvido-{sanitized_name}"
    new_name = new_name[:100] # Enforce Discord's 100-character limit

    try:
        await inter.channel.edit(name=new_name)
        
        # Adiciona um novo campo em vez de alterar o status
        ticket_info["is_resolved"] = True
        
        log_ticket_event(
            inter.channel.id,
            "resolved",
            inter.author.id,
            {"old_name": old_name, "new_name": new_name}
        )
        db.save_document("tickets_data", tickets_data)

        message_content = f"{emoji.double_check} Este ticket foi marcado como resolvido por {inter.author.mention}."

        async def send_resolved_message(destination):
            await destination.send(message_content)

        await send_resolved_message(inter.channel)
        
        try:
            await send_resolved_message(ticket_owner)
        except disnake.Forbidden:
            await inter.channel.send(f"Não foi possível notificar {ticket_owner.mention} por DM. As DMs podem estar desativadas.", delete_after=10)
        
        # Enviar confirmação para o usuário que executou o comando
        await inter.followup.send(f"{emoji.correct} Ticket marcado como resolvido com sucesso!", ephemeral=True)

    except Exception as e:
        print(f"Erro ao marcar ticket como resolvido: {e}")
        await inter.followup.send(f"{emoji.wrong} Ocorreu um erro ao marcar o ticket como resolvido: {e}", ephemeral=True)