import disnake
from functions.database import database as db
from ..logs_tickets import log_ticket_reminder
from functions.emoji import emoji
from functions.perms import perms as perms_check
from ..history import log_ticket_event
from ...utils import SafeFormatter
from ..permissions import get_attendant_roles

async def notify(inter: disnake.MessageInteraction):
    await inter.response.defer(ephemeral=True)

    channel = inter.channel
    config = db.get_document("tickets_config") or {}
    tickets_data = db.get_document("tickets_data") or {}

    found_panel_id = None
    ticket_owner_id = None

    for panel_id, users in tickets_data.get("panels", {}).items():
        for user_id, tickets in users.items():
            for ticket in tickets:
                if ticket.get("ticket_id") == channel.id:
                    found_panel_id = panel_id
                    ticket_owner_id = user_id
                    break
            if found_panel_id:
                break
        if found_panel_id:
            break
    
    if not found_panel_id or not ticket_owner_id:
        return await inter.followup.send("Não foi possível encontrar os dados deste ticket.", ephemeral=True)

    panel_data = config.get("panels", {}).get(found_panel_id)
    if not panel_data:
        return await inter.followup.send("Não foi possível encontrar a configuração do painel associado.", ephemeral=True)

    ticket_owner = inter.guild.get_member(int(ticket_owner_id))
    if not ticket_owner:
        return await inter.followup.send("Não foi possível encontrar o criador do ticket no servidor.", ephemeral=True)

    roles_data = panel_data.get("roles", {})
    atendentes_roles_ids = get_attendant_roles(roles_data)
    user_roles_ids = [role.id for role in inter.author.roles]
    is_atendente = any(role_id in atendentes_roles_ids for role_id in user_roles_ids)
    is_bot_admin = await perms_check.check(inter.author.id)
    is_ticket_owner = inter.author.id == ticket_owner.id
    
    ticket_info = None
    for panel_id, users in tickets_data.get("panels", {}).items():
        if panel_id == found_panel_id:
            for user_id, tickets in users.items():
                if user_id == str(ticket_owner_id):
                    for ticket in tickets:
                        if ticket.get("ticket_id") == channel.id:
                            ticket_info = ticket
                            break
                    break
            break

    if is_atendente or is_bot_admin:
        messages = panel_data.get("messages", {})
        message_template = messages.get("notify_message_staff_to_user", "Olá {user_mention}, você está sendo notificado sobre o seu ticket `{channel_name}`. A equipe de suporte está aguardando sua resposta.")
        
        placeholders = SafeFormatter(
            user_mention=ticket_owner.mention,
            user_name=ticket_owner.name,
            autor_mention=inter.author.mention,
            autor_name=inter.author.name,
            channel_name=channel.name,
            guild_name=inter.guild.name
        )
        notification_message_content = message_template.format_map(placeholders)

        button = disnake.ui.Button(label="Acessar Ticket", style=disnake.ButtonStyle.link, url=channel.jump_url)

        try:
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                primary_color_hex = db.get_document("custom_colors").get("primary")
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title=f"Notificação de Ticket",
                    description=notification_message_content,
                    **embed_kwargs
                )
                await ticket_owner.send(embed=embed, components=[button])
            else:
                await ticket_owner.send(notification_message_content, components=[button])
            
            log_ticket_event(
                channel.id,
                "notify",
                inter.author.id,
                {
                    "notified_user_id": ticket_owner.id,
                    "direction": "staff_to_user"
                }
            )
            db.save_document("tickets_data", tickets_data)
            
            await inter.followup.send(f"Notificação enviada com sucesso para a DM de {ticket_owner.mention}.", ephemeral=True)
            await log_ticket_reminder(inter.bot, channel, inter.author, ticket_owner)
            log_ticket_event(
                channel.id, "notify", inter.author.id, 
                {"direction": "staff_to_user", "notified_user_id": ticket_owner.id}
            )
        except disnake.Forbidden:
            await inter.followup.send(f"Não foi possível enviar a notificação para {ticket_owner.mention}, pois a DM do usuário está fechada.", ephemeral=True)
        except Exception as e:
            await inter.followup.send(f"Ocorreu um erro ao enviar a notificação: {e}", ephemeral=True)
            
    elif is_ticket_owner:
        if ticket_info and ticket_info.get("assumed_by"):
            assignee = inter.guild.get_member(ticket_info["assumed_by"])
            if assignee:
                try:
                    messages = panel_data.get("messages", {})
                    message_template = messages.get("notify_message_user_to_staff", "{user_mention} está solicitando sua atenção no ticket `{channel_name}`.")
                    
                    placeholders = SafeFormatter(
                        user_mention=inter.author.mention,
                        user_name=inter.author.name,
                        atendente_mention=assignee.mention,
                        atendente_name=assignee.name,
                        channel_name=channel.name,
                        guild_name=inter.guild.name
                    )
                    dm_message = message_template.format_map(placeholders)

                    button = disnake.ui.Button(label="Ir para o Ticket", style=disnake.ButtonStyle.link, url=channel.jump_url)
                    await assignee.send(dm_message, components=[button])
                    log_ticket_event(
                        channel.id,
                        "notify",
                        inter.author.id,
                        {
                            "notified_user_id": assignee.id,
                            "direction": "user_to_staff"
                        }
                    )
                    db.save_document("tickets_data", tickets_data)
                    await inter.followup.send(f"O atendente {assignee.mention} foi notificado em sua DM.", ephemeral=True)
                    log_ticket_event(
                        channel.id, "notify", inter.author.id,
                        {"direction": "user_to_staff", "notified_user_id": assignee.id}
                    )
                except disnake.Forbidden:
                    await inter.followup.send(f"Não foi possível notificar o atendente {assignee.mention} via DM. Ele pode ter as DMs fechadas.", ephemeral=True)
            else:
                await inter.followup.send("O atendente que assumiu este ticket não foi encontrado. A notificação não foi enviada.", ephemeral=True)
        else:
            await inter.followup.send("Nenhum atendente assumiu este ticket ainda. Você só poderá notificar após alguém da equipe assumir.", ephemeral=True)
    
    else:
        await inter.followup.send("Você não tem permissão para usar esta função neste ticket.", ephemeral=True)
