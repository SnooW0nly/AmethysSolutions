from functions.database import database as db
from core.enable_intents import enable_intents

class emoji:
    db = db.obter("database/emojis/emojis.json")
    for key, value in db.items():
        locals()[key] = value

def reload_emoji_class():
    """Recarrega a classe emoji com os dados atualizados"""
    emoji.db = db.obter("database/emojis/emojis.json")
    for key, value in emoji.db.items():
        setattr(emoji, key, value)
    print(f"[Emojis] Classe emoji recarregada com {len(emoji.db)} emojis")

def init_on_startup(bot_token: str, app_id: str) -> None:
    """Inicializa e sincroniza emojis na inicialização do bot"""
    print("[Emojis] Iniciando sistema de emojis...")
    
    emojis_data = db.obter("database/emojis/emojis_data.json")
    config_emoji = db.obter("configs/config_emoji.json")

    is_configured = config_emoji.get("isConfigured", False)
    
    # Se isConfigured for true, não sincronizar
    if is_configured:
        print("[Emojis] Sistema de emojis já configurado (isConfigured=true)")
        return
    
    # Se isConfigured for false, verificar os outros requisitos
    configured = emojis_data.get("configured", "false")
    last_token = emojis_data.get("lastToken", "")
    
    print(f"[Emojis] Status: configured={configured}, token_match={last_token == bot_token}")
    
    # Sincronizar se:
    # 1. Nunca foi configurado (configured != "True")
    # 2. Token mudou (last_token diferente do atual)
    should_sync = configured != "True" or (last_token and last_token != bot_token)
    
    if should_sync:
        print("[Emojis] Iniciando sincronização de emojis...")
        # Ativar intents privilegiadas antes de sincronizar emojis
        enable_intents(bot_token, app_id)
        
        from functions.emojis import emojis as Emojis
        emoji_manager = Emojis(bot_token, app_id)
        print(f"[Emojis] Total de emojis a sincronizar: {len(emoji_manager.emojis_db)}")
        emoji_manager.sync_all()
        
        # Recarregar a classe emoji após sincronização
        reload_emoji_class()
    else:
        print("[Emojis] Emojis já sincronizados com o token atual")