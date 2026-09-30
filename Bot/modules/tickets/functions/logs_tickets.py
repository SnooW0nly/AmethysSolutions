import disnake
from functions.database import database as db
from events._common import enviar_log
from functions.emoji import emoji

async def log_ticket_creation(bot, ticket_channel, ticket_owner, panel_name, ticket_mode):
    canais = db.get_document("canais")
    log_channel_id = canais.get("canal_de_logs_de_tickets")
    if not log_channel_id:
        return

    title = "Logs de Tickets - Abertos"
        
    linhas = [
        f"{emoji.textc} **Painel:** {panel_name}",
        f"{emoji.member} **Criador:** {ticket_owner.mention} (`{ticket_owner.id}`)",
        f"{emoji.textc} **Canal/Tópico:** {ticket_channel.mention} (`{ticket_channel.id}`)",
    ]

    guild = ticket_channel.guild
    await enviar_log(guild, int(log_channel_id), title, linhas)


async def log_ticket_closure(bot, ticket_channel, closed_by, ticket_owner, ticket_mode, reason=None):
    canais = db.get_document("canais")
    log_channel_id = canais.get("canal_de_logs_de_tickets")
    if not log_channel_id:
        return
        
    title = "Logs de Tickets - Fechados"
    
    linhas = [
        f"{emoji.textc} **Canal/Tópico:** `{ticket_channel.name}` (`{ticket_channel.id}`)",
    ]
    if ticket_owner:
        linhas.append(f"{emoji.member} **Dono do Ticket:** {ticket_owner.mention} (`{ticket_owner.id}`)")
    
    linhas.append(f"{emoji.member} **Fechado por:** {closed_by.mention} (`{closed_by.id}`)")

    if reason:
        linhas.append(f"{emoji.ban} **Motivo:** {reason}")

    guild = closed_by.guild
    return await enviar_log(guild, int(log_channel_id), title, linhas)


async def log_ticket_reminder(bot, ticket_channel, reminded_by, ticket_owner):
    canais = db.get_document("canais")
    log_channel_id = canais.get("canal_de_logs_de_tickets")
    if not log_channel_id:
        return

    title = "Logs de Tickets - Lembrete"
    
    linhas = [
        f"{emoji.member} **Lembrado por:** {reminded_by.mention} (`{reminded_by.id}`)",
        f"{emoji.member} **Usuário Lembrado:** {ticket_owner.mention} (`{ticket_owner.id}`)",
        f"{emoji.textc} **Ticket:** {ticket_channel.mention} (`{ticket_channel.id}`)",
    ]

    guild = ticket_channel.guild
    await enviar_log(guild, int(log_channel_id), title, linhas)
