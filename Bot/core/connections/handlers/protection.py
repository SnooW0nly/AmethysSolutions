"""Protection module handlers"""

import logging
from functions.database import database as db

logger = logging.getLogger(__name__)

def register_protection_handlers():
    """Register all protection handlers"""
    
    async def get_config(bot, payload):
        config = db.get_document("protection_config") or {}
        return {'config': config}
    
    async def update_config(bot, payload):
        config = payload.get('config', {})
        db.save_document("protection_config", config)
        return {'success': True}
    
    async def get_whitelist(bot, payload):
        whitelist = db.get_document("whitelist") or []
        return {'whitelist': whitelist}
    
    async def get_blacklist(bot, payload):
        blacklist = db.get_document("blacklist") or []
        return {'blacklist': blacklist}
    
    return {
        'protection.getConfig': get_config,
        'protection.updateConfig': update_config,
        'protection.getWhitelist': get_whitelist,
        'protection.getBlacklist': get_blacklist
    }
