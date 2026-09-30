from functions.database import database as db

def carregar_config() -> dict:
    """Carrega a configuração da coleção 'automations_invite_tracker'."""
    data = db.get_document("automations_invite_tracker") or {}
    data.setdefault("ativado", False)
    data.setdefault("channel_id", None)
    data.setdefault("welcome_message", "Seja bem-vindo(a) {member}! Você foi convidado(a) por {inviter} que agora possui {invites} convites válidos.")
    data.setdefault("welcome_message_vanity", "Seja bem-vindo(a) {member}! Você entrou através do Vanity URL do servidor.")
    data.setdefault("leave_message", "Que pena, {member} nos deixou. Ele(a) foi convidado(a) por {inviter} que agora possui {invites} convites válidos.")
    return data

def salvar_config(data: dict) -> None:
    """Salva a configuração na coleção 'automations_invite_tracker'."""
    db.save_document("automations_invite_tracker", data)

def get_invites_data() -> dict:
    """Carrega os dados de convites do documento dedicado 'convites'.
    Se estiver vazio, tenta migrar de automations_invite_tracker.invites_data uma única vez.
    """
    data = db.get_document("convites") or {}
    if data:
        return data

    # Fallback de migração: mover invites_data antigo, se existir
    old_conf = db.get_document("automations_invite_tracker") or {}
    old_invites = old_conf.get("invites_data") if isinstance(old_conf, dict) else None
    if isinstance(old_invites, dict) and old_invites:
        db.save_document("convites", old_invites)
        # remove chave antiga para evitar migração repetida
        try:
            old_conf.pop("invites_data", None)
            db.save_document("automations_invite_tracker", old_conf)
        except Exception:
            pass
        return old_invites
    return {}

def save_invites_data(data: dict) -> None:
    """Salva os dados de convites no documento dedicado 'convites'."""
    db.save_document("convites", data)

# ── Points Tracker ────────────────────────────────────────────────────────────

def get_points_config() -> dict:
    """Carrega a configuração do Points Tracker."""
    data = db.get_document("automations_points_tracker") or {}
    data.setdefault("ativado", False)
    data.setdefault("channel_id", None)
    data.setdefault("recompensas", [])
    data.setdefault("mensagem", {})  # editor_data estilo msg_auto
    return data

def save_points_config(data: dict) -> None:
    db.save_document("automations_points_tracker", data)

def get_points_editor_data() -> dict:
    config = get_points_config()
    return config.get("mensagem", {})

def set_points_editor_data(editor_data: dict):
    config = get_points_config()
    config["mensagem"] = editor_data
    save_points_config(config)

def get_member_invites_valid(guild_id: str, member_id: str) -> int:
    """Retorna o total de convites válidos de um membro."""
    data = get_invites_data()
    guild_data = data.get(str(guild_id), {})
    inv = guild_data.get("invites", {}).get(str(member_id), {})
    return inv.get("valid", 0)

def get_member_invited_list(guild_id: str, member_id: str) -> list:
    """Retorna lista de member_ids que foram convidados pelo membro."""
    data = get_invites_data()
    guild_data = data.get(str(guild_id), {})
    members = guild_data.get("members", {})
    return [mid for mid, mdata in members.items() if (mdata.get("inviter") if isinstance(mdata, dict) else mdata) == str(member_id)]
