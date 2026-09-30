import disnake
from datetime import datetime, timezone, timedelta
from functions.database import database as db
from functions.emoji import emoji

# Timezone UTC-3 (Horário de Brasília)
BRASILIA_TZ = timezone(timedelta(hours=-3))

async def check_permissions(inter: disnake.MessageInteraction, panel_data: dict, option_data: dict = None) -> tuple[bool, str | None]:
    user = inter.author
    user_roles = [role.id for role in user.roles]
    
    roles_config = {}
    if option_data:
        roles_config = option_data.get("roles", {})
    else:
        roles_config = panel_data.get("roles", {})
    
    forbidden_roles = roles_config.get("forbidden", [])
    if forbidden_roles and any(role in forbidden_roles for role in user_roles):
        return False, f"{emoji.wrong} Você está em uma lista de cargos proibidos de abrir ticket."

    allowed_roles = roles_config.get("allowed", [])
    if allowed_roles and not any(role in allowed_roles for role in user_roles):
        return False, f"{emoji.wrong} Você não tem um dos cargos necessários para abrir um ticket."
        
    return True, None

async def check_office_hours(inter: disnake.MessageInteraction, panel_data: dict) -> tuple[bool, str | None]:
    office_hours_data = panel_data.get("office_hours", {})
    if not office_hours_data.get("enabled", False):
        return True, None

    # Usar horário de Brasília (UTC-3)
    now = datetime.now(BRASILIA_TZ)
    start_time_str = office_hours_data.get("start_time")
    end_time_str = office_hours_data.get("end_time")

    if not start_time_str or not end_time_str:
        return True, None

    off_days = office_hours_data.get("off_days", [])
    
    days_map = {0: "seg", 1: "ter", 2: "qua", 3: "qui", 4: "sex", 5: "sab", 6: "dom"}
    current_day_str = days_map[now.weekday()]

    is_off_day = current_day_str in off_days
    
    start_time = datetime.strptime(start_time_str, "%H:%M").time()
    end_time = datetime.strptime(end_time_str, "%H:%M").time()
    is_outside_hours = not (start_time <= now.time() <= end_time)

    if is_off_day or is_outside_hours:
        off_message = office_hours_data.get("message")
        if not off_message:
            off_message = "Nosso horário de atendimento é das {start_time} às {end_time}."
            
        formatted_message = off_message.format(start_time=start_time_str, end_time=end_time_str)
        return False, f"{emoji.clock} {formatted_message}"
        
    return True, None


async def check_existing_ticket(inter: disnake.MessageInteraction, bot, panel_id: str) -> tuple[bool, str | None]:
    user = inter.author
    tickets_data = db.get_document("tickets_data") or {}
    user_tickets = tickets_data.get("panels", {}).get(panel_id, {}).get(str(user.id), [])

    for ticket in user_tickets:
        if ticket.get("status") == "open":
            try:
                existing_channel = bot.get_channel(ticket["ticket_id"]) or await bot.fetch_channel(ticket["ticket_id"])
                if existing_channel:
                    return False, f"{emoji.wrong} Você já possui um ticket aberto em {existing_channel.mention}."
            except (disnake.NotFound, disnake.Forbidden):
                ticket["status"] = "closed"
    
    db.save_document("tickets_data", tickets_data)
    return True, None
