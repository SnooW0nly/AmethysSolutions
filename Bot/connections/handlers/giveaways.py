"""Giveaways module handlers"""

import logging
from functions.database import database as db

logger = logging.getLogger(__name__)

def register_giveaways_handlers():
    """Register all giveaways handlers"""
    
    async def get_active(bot, payload):
        giveaways = db.get_document("giveaways") or {}
        active = [g for g in giveaways.values() if g.get('active')]
        return {'giveaways': active}
    
    async def create(bot, payload):
        data = payload.get('giveawayData', {})
        # TODO: Implement giveaway creation
        return {'success': True, 'message': 'Giveaway created'}
    
    return {
        'giveaways.getActive': get_active,
        'giveaways.create': create
    }
