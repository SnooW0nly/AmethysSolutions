"""
WebSocket initialization event - SIMPLIFIED VERSION
All connections logic removed except mongo_db
"""

import disnake
from disnake.ext import commands
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class WebSocketReady(commands.Cog):
    """Handle bot ready event - simplified without WebSocket connections"""
    
    def __init__(self, bot):
        self.bot = bot
        self.ready_initialized = False
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Bot ready event handler"""
        
        # Prevent multiple initializations
        if self.ready_initialized:
            return
            
        self.ready_initialized = True
        
        # Store bot start time
        if not hasattr(self.bot, 'start_time'):
            self.bot.start_time = datetime.now()
        
        logger.info(f"Bot {self.bot.user.name} is ready!")
        logger.info(f"Bot ID: {self.bot.user.id}")
        logger.info(f"Guilds: {len(self.bot.guilds)}")
    
    @commands.Cog.listener()
    async def on_disconnect(self):
        """Handle bot disconnect"""
        logger.warning("Bot disconnected from Discord")
    
    @commands.Cog.listener()
    async def on_resumed(self):
        """Handle bot resume after disconnect"""
        logger.info("Bot connection resumed")
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        pass

def setup(bot):
    bot.add_cog(WebSocketReady(bot))