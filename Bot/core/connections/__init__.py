"""
WebSocket connections module
"""

from .websocket_manager import WebSocketManager

# Global instance
websocket_manager = None

def setup(bot):
    """Setup WebSocket connections"""
    global websocket_manager
    
    # Create and initialize WebSocket manager
    websocket_manager = WebSocketManager(bot)
    
    # Store reference in bot
    bot.websocket_manager = websocket_manager
    
    return websocket_manager

def get_manager():
    """Get WebSocket manager instance"""
    return websocket_manager
