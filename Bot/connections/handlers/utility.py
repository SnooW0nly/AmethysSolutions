"""Utility handlers for WebSocket"""

import logging
import disnake
from typing import Dict, Any

logger = logging.getLogger(__name__)

def register_utility_handlers():
    """Register all utility handlers"""
    
    async def send_message(bot, payload: dict) -> dict:
        """Send message to channel"""
        try:
            channel_id = payload.get('channelId')
            message = payload.get('message')
            
            if not channel_id or not message:
                raise ValueError("channelId and message are required")
            
            channel = bot.get_channel(int(channel_id))
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")
            
            sent_message = await channel.send(message)
            
            return {
                'success': True,
                'messageId': str(sent_message.id),
                'channelId': str(channel.id)
            }
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def send_embed(bot, payload: dict) -> dict:
        """Send embed to channel"""
        try:
            channel_id = payload.get('channelId')
            embed_data = payload.get('embed')
            
            if not channel_id or not embed_data:
                raise ValueError("channelId and embed are required")
            
            channel = bot.get_channel(int(channel_id))
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")
            
            # Create embed
            embed = disnake.Embed(
                title=embed_data.get('title'),
                description=embed_data.get('description'),
                color=int(embed_data.get('color', '0x2F3136'), 16) if embed_data.get('color') else None
            )
            
            if embed_data.get('author'):
                embed.set_author(
                    name=embed_data['author'].get('name'),
                    icon_url=embed_data['author'].get('icon_url'),
                    url=embed_data['author'].get('url')
                )
            
            if embed_data.get('thumbnail'):
                embed.set_thumbnail(url=embed_data['thumbnail'])
            
            if embed_data.get('image'):
                embed.set_image(url=embed_data['image'])
            
            if embed_data.get('footer'):
                embed.set_footer(
                    text=embed_data['footer'].get('text'),
                    icon_url=embed_data['footer'].get('icon_url')
                )
            
            # Add fields
            for field in embed_data.get('fields', []):
                embed.add_field(
                    name=field.get('name'),
                    value=field.get('value'),
                    inline=field.get('inline', False)
                )
            
            sent_message = await channel.send(embed=embed)
            
            return {
                'success': True,
                'messageId': str(sent_message.id),
                'channelId': str(channel.id)
            }
        except Exception as e:
            logger.error(f"Error sending embed: {e}")
            raise
    
    async def announce(bot, payload: dict) -> dict:
        """Make announcement"""
        try:
            channel_id = payload.get('channelId')
            announcement = payload.get('announcement')
            
            if not channel_id or not announcement:
                raise ValueError("channelId and announcement are required")
            
            channel = bot.get_channel(int(channel_id))
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")
            
            # Create announcement embed
            embed = disnake.Embed(
                title=announcement.get('title', '📢 Anúncio'),
                description=announcement.get('content'),
                color=disnake.Color.blue()
            )
            
            if announcement.get('image'):
                embed.set_image(url=announcement['image'])
            
            if announcement.get('thumbnail'):
                embed.set_thumbnail(url=announcement['thumbnail'])
            
            # Add timestamp
            embed.timestamp = disnake.utils.utcnow()
            
            # Set footer
            embed.set_footer(
                text=announcement.get('footer', bot.user.name),
                icon_url=bot.user.display_avatar.url if bot.user else None
            )
            
            # Send with mention if specified
            content = None
            if announcement.get('mention_everyone'):
                content = "@everyone"
            elif announcement.get('mention_here'):
                content = "@here"
            elif announcement.get('mention_role'):
                role = channel.guild.get_role(int(announcement['mention_role']))
                if role:
                    content = role.mention
            
            sent_message = await channel.send(content=content, embed=embed)
            
            return {
                'success': True,
                'messageId': str(sent_message.id),
                'channelId': str(channel.id)
            }
        except Exception as e:
            logger.error(f"Error making announcement: {e}")
            raise
    
    async def create_invite(bot, payload: dict) -> dict:
        """Create server invite"""
        try:
            channel_id = payload.get('channelId')
            options = payload.get('options', {})
            
            if channel_id:
                channel = bot.get_channel(int(channel_id))
            else:
                # Get first text channel
                import json
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                guild_id = int(config.get('bot', {}).get('server'))
                guild = bot.get_guild(guild_id)
                channel = guild.text_channels[0] if guild else None
            
            if not channel:
                raise ValueError("No valid channel found")
            
            # Create invite
            invite = await channel.create_invite(
                max_age=options.get('maxAge', 86400),  # Default 24 hours
                max_uses=options.get('maxUses', 0),  # 0 = unlimited
                temporary=options.get('temporary', False),
                unique=options.get('unique', True)
            )
            
            return {
                'success': True,
                'code': invite.code,
                'url': invite.url,
                'channelId': str(channel.id),
                'channelName': channel.name
            }
        except Exception as e:
            logger.error(f"Error creating invite: {e}")
            raise
    
    return {
        'utility.sendMessage': send_message,
        'utility.sendEmbed': send_embed,
        'utility.announce': announce,
        'utility.createInvite': create_invite
    }
