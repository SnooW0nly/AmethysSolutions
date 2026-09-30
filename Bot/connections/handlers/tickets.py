"""Tickets module handlers for WebSocket"""

import logging
from typing import Dict, Any
from functions.database import database as db

logger = logging.getLogger(__name__)

def register_tickets_handlers():
    """Register all tickets-related handlers"""
    
    async def get_config(bot, payload: dict) -> dict:
        """Get tickets configuration"""
        try:
            config = db.get_document("tickets_config") or {}
            return {'config': config}
        except Exception as e:
            logger.error(f"Error getting tickets config: {e}")
            raise
    
    async def update_config(bot, payload: dict) -> dict:
        """Update tickets configuration"""
        try:
            config = payload.get('config', {})
            db.save_document("tickets_config", config)
            return {'success': True, 'message': 'Configuration updated'}
        except Exception as e:
            logger.error(f"Error updating tickets config: {e}")
            raise
    
    async def get_categories(bot, payload: dict) -> dict:
        """Get ticket categories"""
        try:
            categories = db.get_document("ticket_categories") or {}
            return {'categories': list(categories.values())}
        except Exception as e:
            logger.error(f"Error getting ticket categories: {e}")
            raise
    
    async def get_active_tickets(bot, payload: dict) -> dict:
        """Get active tickets"""
        try:
            tickets = db.get_document("tickets") or {}
            active = [t for t in tickets.values() if t.get('status') == 'open']
            return {'tickets': active, 'count': len(active)}
        except Exception as e:
            logger.error(f"Error getting active tickets: {e}")
            raise
    
    return {
        'tickets.getConfig': get_config,
        'tickets.updateConfig': update_config,
        'tickets.getCategories': get_categories,
        'tickets.getActiveTickets': get_active_tickets
    }
