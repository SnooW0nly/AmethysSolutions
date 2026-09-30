import disnake
import time
from functions.database import database as db
from functions.emoji import emoji
from ..history import log_ticket_event
from ..permissions import check_attendant_permissions

class UnarchiveView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(disnake.ui.Button(label="Desarquivar", emoji=emoji.unlock, custom_id="ticket_unarchive"))

async def archive_ticket(inter: disnake.MessageInteraction):
    """Arquiva um canal ou tópico de ticket."""
    await inter.response.defer(ephemeral=True)
    
    # Verificar permissões
    has_permission = await check_attendant_permissions(inter.author, inter.channel.id)
    if not has_permission:
        return await inter.followup.send(
            f"{emoji.wrong} Você não tem permissão para usar este comando.",
            ephemeral=True
        )
    
    tickets_data = db.get_document("tickets_data") or {}
    
    ticket_info, panel_id_found, owner_id = None, None, None
    for panel_id, users in tickets_data.get("panels", {}).items():
        for user_id, tickets in users.items():
            for t in tickets:
                if t.get("ticket_id") == inter.channel.id:
                    ticket_info, panel_id_found, owner_id = t, panel_id, user_id
                    break
            if ticket_info: break
        if ticket_info: break

    if not ticket_info:
        return await inter.followup.send("Este canal não parece ser um ticket válido.", ephemeral=True)

    if ticket_info.get("status") == "closed":
        return await inter.followup.send("Você não pode arquivar um ticket que já foi fechado.", ephemeral=True)

    # Permite re-arquivar um tópico que foi desarquivado manualmente
    is_thread_manually_unarchived = (
        isinstance(inter.channel, disnake.Thread) and
        ticket_info.get("archived") and
        not inter.channel.archived
    )
    if ticket_info.get("archived") and not is_thread_manually_unarchived:
        return await inter.followup.send("Este ticket já está arquivado.", ephemeral=True)

    if isinstance(inter.channel, disnake.Thread):
        try:
            await inter.channel.edit(archived=True)
        except Exception as e:
            return await inter.followup.send(f"Ocorreu um erro ao arquivar o tópico: {e}", ephemeral=True)
    else:
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id_found, {})
        atendentes_roles_ids = panel_data.get("roles", {}).get("atendentes", [])
        
        ticket_owner_member = inter.guild.get_member(int(owner_id))

        overwrites = inter.channel.overwrites

        # Nega o envio de mensagens para @everyone, mantendo outras perms (como ver canal)
        everyone_overwrite = overwrites.get(inter.guild.default_role, disnake.PermissionOverwrite())
        everyone_overwrite.send_messages = False
        overwrites[inter.guild.default_role] = everyone_overwrite

        # Permite o envio de mensagens para atendentes
        for role_id in atendentes_roles_ids:
            role = inter.guild.get_role(int(role_id))
            if role:
                attendant_overwrite = overwrites.get(role, disnake.PermissionOverwrite())
                attendant_overwrite.send_messages = True
                overwrites[role] = attendant_overwrite
        
        # Nega explicitamente o envio de mensagens para o dono do ticket
        if ticket_owner_member:
            owner_overwrite = overwrites.get(ticket_owner_member, disnake.PermissionOverwrite())
            owner_overwrite.send_messages = False
            overwrites[ticket_owner_member] = owner_overwrite

        try:
            await inter.channel.edit(overwrites=overwrites)
            await inter.channel.send(
                f"{emoji.arrow} Este ticket foi arquivado por {inter.author.mention}\nNão é será possivel enviar mensagens no canal.",
                view=UnarchiveView()
            )
            await inter.followup.send("Ticket arquivado com sucesso!", ephemeral=True)
        except disnake.Forbidden:
            return await inter.followup.send("Não tenho permissão para editar as permissões deste canal.", ephemeral=True)
        except Exception as e:
            return await inter.followup.send(f"Ocorreu um erro ao arquivar o ticket: {e}", ephemeral=True)

    ticket_info["archived"] = True
    log_ticket_event(inter.channel.id, "archive", inter.author.id, {"status": "archived"})
    db.save_document("tickets_data", tickets_data)


async def unarchive_ticket(inter: disnake.MessageInteraction):
    """Desarquiva um canal ou tópico de ticket."""
    await inter.response.defer(ephemeral=True)
    
    tickets_data = db.get_document("tickets_data") or {}
    
    ticket_info, panel_id_found, owner_id = None, None, None
    for panel_id, users in tickets_data.get("panels", {}).items():
        for user_id, tickets in users.items():
            for t in tickets:
                if t.get("ticket_id") == inter.channel.id:
                    ticket_info, panel_id_found, owner_id = t, panel_id, user_id
                    break
            if ticket_info: break
        if ticket_info: break

    if not ticket_info or not ticket_info.get("archived"):
        return await inter.followup.send("Este ticket não está arquivado.", ephemeral=True)

    if isinstance(inter.channel, disnake.Thread):
        try:
            await inter.channel.edit(archived=False)
            await inter.edit_original_response(content="Tópico desarquivado com sucesso!", view=None)
            await inter.channel.send(f"{emoji.unlock} Este ticket foi desarquivado por {inter.author.mention}.")
        except Exception as e:
            return await inter.followup.send(f"Ocorreu um erro ao desarquivar o tópico: {e}", ephemeral=True)
    else:
        ticket_owner_member = inter.guild.get_member(int(owner_id))
        overwrites = inter.channel.overwrites

        # Restaura a permissão de envio para o dono do ticket
        if ticket_owner_member:
            owner_overwrite = overwrites.get(ticket_owner_member, disnake.PermissionOverwrite())
            owner_overwrite.send_messages = True
            overwrites[ticket_owner_member] = owner_overwrite
        else: # Se o membro não for encontrado, restaura @everyone para garantir que o ticket não fique travado
            everyone_overwrite = overwrites.get(inter.guild.default_role, disnake.PermissionOverwrite())
            everyone_overwrite.send_messages = None # Herdar da categoria
            overwrites[inter.guild.default_role] = everyone_overwrite


        try:
            await inter.channel.edit(overwrites=overwrites)
            await inter.message.delete()
            await inter.channel.send(f"{emoji.unlock} Este ticket foi desarquivado por {inter.author.mention}.")
        except disnake.Forbidden:
            return await inter.followup.send("Não tenho permissão para editar as permissões deste canal.", ephemeral=True)
        except Exception as e:
            return await inter.followup.send(f"Ocorreu um erro ao desarquivar o ticket: {e}", ephemeral=True)

    ticket_info["archived"] = False
    log_ticket_event(inter.channel.id, "archive", inter.author.id, {"status": "unarchived"})
    db.save_document("tickets_data", tickets_data)
