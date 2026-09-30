"""
Sistema centralizado de verificação de permissões para tickets
"""
import disnake
from functions.database import database as db
from functions.perms import perms


def get_attendant_roles(roles_data: dict) -> list[int]:
    """
    Obtém os IDs dos cargos de atendente com fallback para cargo_suporte.
    
    Args:
        roles_data: Dicionário com configuração de roles (pode ser de panel ou option)
    
    Returns:
        Lista de IDs de cargos de atendente
    """
    atendentes_roles_ids = roles_data.get("mention", [])
    
    # Se não houver cargos configurados, usar fallback para cargo_suporte
    if not atendentes_roles_ids:
        cargos_config = db.get_document("cargos") or {}
        cargo_suporte_id = cargos_config.get("cargo_suporte")
        if cargo_suporte_id:
            atendentes_roles_ids = [int(cargo_suporte_id)]
    
    return atendentes_roles_ids


async def check_attendant_permissions(
    user: disnake.Member,
    channel_id: int,
    check_bot_admin: bool = True
) -> bool:
    """
    Verifica se o usuário tem permissões de atendente para o ticket.
    
    Args:
        user: Membro a verificar
        channel_id: ID do canal do ticket
        check_bot_admin: Se True, admins do bot sempre têm permissão
    
    Returns:
        True se o usuário tem permissão, False caso contrário
    """
    # Verificar se é admin do bot primeiro
    if check_bot_admin:
        is_bot_admin = await perms.check(user.id)
        if is_bot_admin:
            return True
    
    # Buscar informações do ticket
    tickets_data = db.get_document("tickets_data") or {} or {}
    ticket_config = db.get_document("tickets_config") or {} or {}
    
    # Encontrar o painel e opção do ticket
    panel_id = None
    ticket_info = None
    
    for pid, users in tickets_data.get("panels", {}).items():
        if not isinstance(users, dict):
            continue
        for uid, tickets in users.items():
            for ticket in tickets:
                if ticket.get("ticket_id") == channel_id:
                    panel_id = pid
                    ticket_info = ticket
                    break
            if panel_id:
                break
        if panel_id:
            break
    
    if not panel_id or not ticket_info:
        return False
    
    # Obter configuração do painel
    panel_config = ticket_config.get("panels", {}).get(panel_id, {})
    if not panel_config:
        return False
    
    # Obter option_id se existir
    option_id = ticket_info.get("option_id")
    option_data = None
    if option_id:
        option_data = next(
            (opt for opt in panel_config.get("options", []) if str(opt.get("id")) == str(option_id)),
            None
        )
    
    # Obter cargos de atendente do painel e da opção
    panel_roles = panel_config.get("roles", {})
    option_roles = option_data.get("roles", {}) if option_data else {}
    
    # Pegar cargos de atendentes (mention é o campo usado para atendentes)
    panel_atendente_roles = panel_roles.get("atendentes", []) or panel_roles.get("mention", [])
    option_atendente_roles = option_roles.get("atendentes", []) or option_roles.get("mention", [])
    
    # Combinar ambos (prioridade para opção, mas aceita ambos)
    atendente_roles_ids = list(set(panel_atendente_roles + option_atendente_roles))
    
    # Se não houver cargos configurados, usar fallback para cargo_suporte
    if not atendente_roles_ids:
        cargos_config = db.get_document("cargos") or {}
        cargo_suporte_id = cargos_config.get("cargo_suporte")
        if cargo_suporte_id:
            atendente_roles_ids = [int(cargo_suporte_id)]
        else:
            return False
    
    # Verificar se o usuário tem algum dos cargos
    user_roles = [role.id for role in user.roles]
    has_permission = any(role_id in user_roles for role_id in atendente_roles_ids)
    
    return has_permission


def find_ticket_panel_and_config(channel_id: int) -> tuple[str | None, dict, dict | None]:
    """
    Encontra o painel e configuração de um ticket pelo ID do canal.
    
    Returns:
        Tupla com (panel_id, panel_config, ticket_info)
    """
    tickets_data = db.get_document("tickets_data") or {} or {}
    ticket_config = db.get_document("tickets_config") or {} or {}
    
    for panel_id, users in tickets_data.get("panels", {}).items():
        if not isinstance(users, dict):
            continue
        for uid, tickets in users.items():
            for ticket in tickets:
                if ticket.get("ticket_id") == channel_id:
                    panel_config = ticket_config.get("panels", {}).get(panel_id, {})
                    return panel_id, panel_config, ticket
    
    return None, {}, None
