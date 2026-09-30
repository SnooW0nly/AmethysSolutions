"""
WebSocket function handlers for Sync Bot
"""

from .loja import register_loja_handlers
from .tickets import register_tickets_handlers
from .giveaways import register_giveaways_handlers
from .protection import register_protection_handlers
from .automations import register_automations_handlers
from .customization import register_customization_handlers
from .rendimentos import register_rendimentos_handlers
from .cloud import register_cloud_handlers
from .settings import register_settings_handlers
from .guild import register_guild_handlers
from .bot import register_bot_handlers
from .utility import register_utility_handlers
from .database import register_database_handlers

def register_all_handlers():
    """Register all function handlers"""
    handlers = {}
    
    # Register module handlers
    handlers.update(register_loja_handlers())
    handlers.update(register_tickets_handlers())
    handlers.update(register_giveaways_handlers())
    handlers.update(register_protection_handlers())
    handlers.update(register_automations_handlers())
    handlers.update(register_customization_handlers())
    handlers.update(register_rendimentos_handlers())
    handlers.update(register_cloud_handlers())
    handlers.update(register_settings_handlers())
    handlers.update(register_guild_handlers())
    handlers.update(register_bot_handlers())
    handlers.update(register_utility_handlers())
    handlers.update(register_database_handlers())
    
    return handlers
