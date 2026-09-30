"""Rendimentos module handlers"""

import logging
from functions.database import database as db

logger = logging.getLogger(__name__)

def register_rendimentos_handlers():
    """Register all rendimentos handlers"""
    
    async def get_config(bot, payload):
        config = db.get_document("rendimentos_config") or {}
        return {'config': config}
    
    async def get_earnings(bot, payload):
        earnings = db.get_document("earnings") or {}
        return {'earnings': earnings}
    
    return {
        'rendimentos.getConfig': get_config,
        'rendimentos.getEarnings': get_earnings
    }
