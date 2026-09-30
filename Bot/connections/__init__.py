"""
WebSocket connections module
"""

from .ws_manager import WSManager

# Global instance
ws_manager = None

def setup(bot):
    """Setup WebSocket connections"""
    global ws_manager
    ws_manager = WSManager(bot)
    bot.ws_manager = ws_manager
    return ws_manager

async def initialize(bot):
    """Initialize and connect WebSocket"""
    global ws_manager
    if ws_manager is None:
        ws_manager = setup(bot)
    await ws_manager.initialize()
    return ws_manager

def get_manager():
    """Get WebSocket manager instance"""
    return ws_manager

# Extensions WebSocket
async def initialize_extensions(bot):
    """Initialize and connect Extensions WebSocket"""
    from .extensions_ws import get_extensions_ws
    ws = get_extensions_ws(bot)
    bot.extensions_ws = ws
    await ws.initialize()
    return ws

def get_extensions_manager():
    """Get Extensions WebSocket manager instance (singleton já inicializado)"""
    from .extensions_ws import get_extensions_ws
    try:
        return get_extensions_ws()
    except ValueError:
        return None

# Backwards compatibility
websocket_manager = None
WebSocketManager = WSManager