"""
Funções auxiliares para verificação de preferências da loja
"""

from datetime import datetime
from typing import Optional, Tuple
from functions.database import database as db


def check_store_hours() -> Tuple[bool, Optional[str]]:
    """
    Verifica se a loja está dentro do horário de funcionamento
    Retorna: (is_open, message)
    """
    prefs = db.get_document("loja_preferences") or {}
    office_hours = prefs.get("office_hours", {})
    
    if not office_hours.get("enabled", False):
        return True, None  # Sem restrição de horário
    
    start_time = office_hours.get("start_time", "")
    end_time = office_hours.get("end_time", "")
    off_days = office_hours.get("off_days", [])
    custom_message = office_hours.get("message", "")
    
    if not start_time or not end_time:
        return True, None  # Horário não configurado corretamente
    
    # Verificar dia da semana
    current_day = datetime.now().strftime("%a").lower()[:3]  # seg, ter, qua, etc.
    day_map = {
        "mon": "seg", "tue": "ter", "wed": "qua", "thu": "qui",
        "fri": "sex", "sat": "sab", "sun": "dom"
    }
    current_day_pt = day_map.get(current_day, current_day)
    
    if current_day_pt in off_days:
        # Fora de funcionamento neste dia
        if custom_message:
            message = custom_message.format(
                start_time=start_time,
                end_time=end_time
            )
        else:
            message = f"A loja não funciona aos {', '.join(off_days)}."
        return False, message
    
    # Verificar horário
    try:
        current_time = datetime.now().strftime("%H:%M")
        start_hour, start_min = map(int, start_time.split(":"))
        end_hour, end_min = map(int, end_time.split(":"))
        current_hour, current_min = map(int, current_time.split(":"))
        
        current_minutes = current_hour * 60 + current_min
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        # Se o horário de fechamento é no dia seguinte (ex: 23:00 - 02:00)
        if end_minutes < start_minutes:
            is_open = current_minutes >= start_minutes or current_minutes < end_minutes
        else:
            is_open = start_minutes <= current_minutes < end_minutes
        
        if not is_open:
            if custom_message:
                message = custom_message.format(
                    start_time=start_time,
                    end_time=end_time
                )
            else:
                message = f"Nosso horário de atendimento é das {start_time} às {end_time}."
            return False, message
        
        return True, None
    except Exception:
        # Erro ao processar horário, permitir compra
        return True, None


def get_terms() -> Tuple[bool, Optional[str]]:
    """
    Obtém os termos da loja se estiverem habilitados
    Retorna: (enabled, terms_text)
    """
    prefs = db.get_document("loja_preferences") or {}
    terms = prefs.get("terms", {})
    
    if not terms.get("enabled", False):
        return False, None
    
    terms_text = terms.get("text", "")
    if not terms_text:
        return False, None
    
    return True, terms_text


def check_maintenance(user_id: Optional[int] = None, guild: Optional[object] = None) -> Tuple[bool, Optional[str]]:
    """
    Verifica se a loja está em manutenção
    Retorna: (is_maintenance, message)
    """
    maintenance = db.get_document("loja_maintenance") or {}
    
    if not maintenance.get("enabled", False):
        return False, None
    
    # Verificar se é admin e se admins podem comprar
    allow_admins = maintenance.get("allow_admins", True)
    if allow_admins and user_id and guild:
        try:
            cargos = db.get_document("cargos") or {}
            admin_role_id = cargos.get("cargo_admin")
            if admin_role_id:
                member = guild.get_member(user_id)
                if member:
                    if any(role.id == int(admin_role_id) for role in member.roles):
                        return False, None  # Admin pode comprar
        except:
            pass
    
    # Verificar permissões de administrador do Discord
    if allow_admins and user_id and guild:
        try:
            member = guild.get_member(user_id)
            if member and member.guild_permissions.administrator:
                return False, None  # Admin pode comprar
        except:
            pass
    
    # Loja em manutenção
    message = maintenance.get("message", "Olá, {user} a loja está em manutenção, tente novamente mais tarde.")
    
    # Substituir {user} pela menção do usuário se possível
    if user_id and guild:
        try:
            user = guild.get_member(user_id)
            if user:
                message = message.replace("{user}", user.mention)
        except:
            message = message.replace("{user}", "você")
    else:
        message = message.replace("{user}", "você")
    
    return True, message

