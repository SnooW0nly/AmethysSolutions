"""
Bot management handlers for WebSocket
"""

import logging
import os
import sys
from typing import Dict, Any
from datetime import datetime
import psutil
import disnake

logger = logging.getLogger(__name__)

def register_bot_handlers():
    """Register all bot-related handlers"""
    
    async def get_status(bot, payload: dict) -> dict:
        """Get bot status"""
        try:
            # Get process info
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            return {
                'status': 'online',
                'uptime': (datetime.now() - bot.start_time).total_seconds() if hasattr(bot, 'start_time') else 0,
                'latency': bot.latency * 1000,  # Convert to ms
                'guilds': len(bot.guilds),
                'users': len(bot.users),
                'commands': len(bot.slash_commands),
                'memory': {
                    'rss': memory_info.rss / 1024 / 1024,  # MB
                    'percent': process.memory_percent()
                },
                'cpu': process.cpu_percent(),
                'version': bot.version if hasattr(bot, 'version') else '1.0.0',
                'python': sys.version,
                'disnake': disnake.__version__
            }
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            raise
    
    async def restart(bot, payload: dict) -> dict:
        """Restart bot"""
        try:
            logger.info("Bot restart requested via WebSocket")
            
            # Schedule restart
            import asyncio
            asyncio.create_task(_restart_bot(bot))
            
            return {
                'success': True,
                'message': 'Bot restart initiated'
            }
        except Exception as e:
            logger.error(f"Error restarting bot: {e}")
            raise
    
    async def get_logs(bot, payload: dict) -> dict:
        """Get bot logs"""
        try:
            lines = payload.get('lines', 100)
            level = payload.get('level', 'all')
            
            # Read log file
            log_file = 'bot.log'
            logs = []
            
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8') as f:
                    all_lines = f.readlines()
                    
                    # Get last N lines
                    recent_lines = all_lines[-lines:] if lines > 0 else all_lines
                    
                    # Filter by level if specified
                    for line in recent_lines:
                        if level == 'all' or level.upper() in line:
                            logs.append(line.strip())
            
            return {
                'logs': logs,
                'count': len(logs)
            }
        except Exception as e:
            logger.error(f"Error getting logs: {e}")
            raise
    
    async def clear_cache(bot, payload: dict) -> dict:
        """Clear bot cache"""
        try:
            # Clear various caches
            cleared = []
            
            # Clear message cache
            if hasattr(bot, '_connection'):
                bot._connection._messages.clear()
                cleared.append('messages')
            
            # Clear member cache for all guilds
            for guild in bot.guilds:
                guild._members.clear()
                cleared.append(f'guild_{guild.id}_members')
            
            # Run garbage collection
            import gc
            gc.collect()
            
            return {
                'success': True,
                'message': 'Cache cleared',
                'cleared': cleared
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            raise
    
    async def get_stats(bot, payload: dict) -> dict:
        """Get bot statistics"""
        try:
            from functions.database import database as db
            
            # Get various stats
            stats = {
                'commands': {
                    'total': len(bot.slash_commands),
                    'global': len([c for c in bot.slash_commands if c.guild_ids is None]),
                    'guild': len([c for c in bot.slash_commands if c.guild_ids is not None])
                },
                'events': {
                    'listeners': len(bot._listeners),
                    'handlers': len(bot.extra_events)
                },
                'cache': {
                    'guilds': len(bot.guilds),
                    'users': len(bot.users),
                    'emojis': len(bot.emojis),
                    'messages': len(bot.cached_messages) if hasattr(bot, 'cached_messages') else 0
                },
                'database': {
                    'products': len(db.get_document("loja_products") or {}),
                    'orders': len(db.get_document("orders") or {}),
                    'tickets': len(db.get_document("tickets") or {}),
                    'giveaways': len(db.get_document("giveaways") or {})
                }
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            raise
    
    async def update_presence(bot, payload: dict) -> dict:
        """Update bot presence"""
        try:
            presence = payload.get('presence', {})
            
            # Parse activity type
            activity_type = presence.get('type', 'playing').lower()
            activity_types = {
                'playing': disnake.ActivityType.playing,
                'streaming': disnake.ActivityType.streaming,
                'listening': disnake.ActivityType.listening,
                'watching': disnake.ActivityType.watching,
                'competing': disnake.ActivityType.competing
            }
            
            # Parse status
            status_type = presence.get('status', 'online').lower()
            status_types = {
                'online': disnake.Status.online,
                'idle': disnake.Status.idle,
                'dnd': disnake.Status.dnd,
                'invisible': disnake.Status.invisible
            }
            
            # Create activity
            activity = None
            if presence.get('name'):
                activity = disnake.Activity(
                    type=activity_types.get(activity_type, disnake.ActivityType.playing),
                    name=presence['name'],
                    url=presence.get('url') if activity_type == 'streaming' else None
                )
            
            # Update presence
            await bot.change_presence(
                activity=activity,
                status=status_types.get(status_type, disnake.Status.online)
            )
            
            return {
                'success': True,
                'message': 'Presence updated'
            }
        except Exception as e:
            logger.error(f"Error updating presence: {e}")
            raise
    
    async def _restart_bot(bot):
        """Internal function to restart bot"""
        await asyncio.sleep(2)  # Wait 2 seconds
        logger.info("Restarting bot...")
        
        # Close connections
        await bot.close()
        
        # Restart process
        os.execv(sys.executable, ['python'] + sys.argv)
    
    return {
        'bot.getStatus': get_status,
        'bot.restart': restart,
        'bot.getLogs': get_logs,
        'bot.clearCache': clear_cache,
        'bot.getStats': get_stats,
        'bot.updatePresence': update_presence
    }
