"""
Guild/Server information handlers for WebSocket
"""

import logging
from typing import Dict, Any
import disnake

logger = logging.getLogger(__name__)

def register_guild_handlers():
    """Register all guild-related handlers"""
    
    async def get_info(bot, payload: dict) -> dict:
        """Get guild information"""
        try:
            # Get main guild from config
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            return {
                'id': str(guild.id),
                'name': guild.name,
                'icon': str(guild.icon.url) if guild.icon else None,
                'banner': str(guild.banner.url) if guild.banner else None,
                'description': guild.description,
                'memberCount': guild.member_count,
                'premiumTier': guild.premium_tier,
                'premiumSubscriptionCount': guild.premium_subscription_count,
                'preferredLocale': str(guild.preferred_locale),
                'features': guild.features,
                'createdAt': guild.created_at.isoformat(),
                'ownerId': str(guild.owner_id)
            }
        except Exception as e:
            logger.error(f"Error getting guild info: {e}")
            raise
    
    async def get_channels(bot, payload: dict) -> dict:
        """Get all channels"""
        try:
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            channels = []
            for channel in guild.channels:
                channel_data = {
                    'id': str(channel.id),
                    'name': channel.name,
                    'type': str(channel.type),
                    'position': channel.position
                }
                
                # Add category info
                if hasattr(channel, 'category') and channel.category:
                    channel_data['categoryId'] = str(channel.category.id)
                    channel_data['categoryName'] = channel.category.name
                
                # Add text channel specific info
                if isinstance(channel, disnake.TextChannel):
                    channel_data['topic'] = channel.topic
                    channel_data['nsfw'] = channel.nsfw
                    channel_data['slowmode'] = channel.slowmode_delay
                
                # Add voice channel specific info
                elif isinstance(channel, disnake.VoiceChannel):
                    channel_data['bitrate'] = channel.bitrate
                    channel_data['userLimit'] = channel.user_limit
                    channel_data['rtcRegion'] = str(channel.rtc_region) if channel.rtc_region else None
                
                channels.append(channel_data)
            
            # Sort by position and type
            channels.sort(key=lambda x: (x['type'], x['position']))
            
            return {
                'channels': channels,
                'count': len(channels)
            }
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            raise
    
    async def get_roles(bot, payload: dict) -> dict:
        """Get all roles"""
        try:
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            roles = []
            for role in guild.roles:
                roles.append({
                    'id': str(role.id),
                    'name': role.name,
                    'color': str(role.color),
                    'position': role.position,
                    'permissions': role.permissions.value,
                    'mentionable': role.mentionable,
                    'hoist': role.hoist,
                    'managed': role.managed,
                    'memberCount': len(role.members)
                })
            
            # Sort by position (highest first)
            roles.sort(key=lambda x: x['position'], reverse=True)
            
            return {
                'roles': roles,
                'count': len(roles)
            }
        except Exception as e:
            logger.error(f"Error getting roles: {e}")
            raise
    
    async def get_members(bot, payload: dict) -> dict:
        """Get members list"""
        try:
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            limit = payload.get('limit', 100)
            offset = payload.get('offset', 0)
            
            members = []
            member_list = list(guild.members)[offset:offset + limit]
            
            for member in member_list:
                members.append({
                    'id': str(member.id),
                    'username': member.name,
                    'displayName': member.display_name,
                    'discriminator': member.discriminator,
                    'avatar': str(member.display_avatar.url) if member.display_avatar else None,
                    'bot': member.bot,
                    'status': str(member.status),
                    'joinedAt': member.joined_at.isoformat() if member.joined_at else None,
                    'roles': [str(role.id) for role in member.roles if role.id != guild.id],
                    'premiumSince': member.premium_since.isoformat() if member.premium_since else None
                })
            
            return {
                'members': members,
                'count': len(members),
                'total': guild.member_count,
                'hasMore': (offset + limit) < guild.member_count
            }
        except Exception as e:
            logger.error(f"Error getting members: {e}")
            raise
    
    async def get_member(bot, payload: dict) -> dict:
        """Get specific member"""
        try:
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            member_id = payload.get('memberId')
            if not member_id:
                raise ValueError("memberId is required")
            
            member = guild.get_member(int(member_id))
            if not member:
                raise ValueError(f"Member {member_id} not found")
            
            return {
                'member': {
                    'id': str(member.id),
                    'username': member.name,
                    'displayName': member.display_name,
                    'discriminator': member.discriminator,
                    'avatar': str(member.display_avatar.url) if member.display_avatar else None,
                    'bot': member.bot,
                    'status': str(member.status),
                    'joinedAt': member.joined_at.isoformat() if member.joined_at else None,
                    'createdAt': member.created_at.isoformat(),
                    'roles': [
                        {
                            'id': str(role.id),
                            'name': role.name,
                            'color': str(role.color)
                        }
                        for role in member.roles if role.id != guild.id
                    ],
                    'premiumSince': member.premium_since.isoformat() if member.premium_since else None,
                    'permissions': member.guild_permissions.value
                }
            }
        except Exception as e:
            logger.error(f"Error getting member: {e}")
            raise
    
    async def get_emojis(bot, payload: dict) -> dict:
        """Get server emojis"""
        try:
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            emojis = []
            for emoji in guild.emojis:
                emojis.append({
                    'id': str(emoji.id),
                    'name': emoji.name,
                    'animated': emoji.animated,
                    'url': str(emoji.url),
                    'createdAt': emoji.created_at.isoformat()
                })
            
            return {
                'emojis': emojis,
                'count': len(emojis),
                'limit': guild.emoji_limit
            }
        except Exception as e:
            logger.error(f"Error getting emojis: {e}")
            raise
    
    async def get_stats(bot, payload: dict) -> dict:
        """Get server statistics"""
        try:
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            # Count channel types
            text_channels = len([c for c in guild.channels if isinstance(c, disnake.TextChannel)])
            voice_channels = len([c for c in guild.channels if isinstance(c, disnake.VoiceChannel)])
            categories = len(guild.categories)
            
            # Count member stats
            total_members = guild.member_count
            humans = len([m for m in guild.members if not m.bot])
            bots = len([m for m in guild.members if m.bot])
            online = len([m for m in guild.members if m.status != disnake.Status.offline])
            
            return {
                'stats': {
                    'members': {
                        'total': total_members,
                        'humans': humans,
                        'bots': bots,
                        'online': online
                    },
                    'channels': {
                        'text': text_channels,
                        'voice': voice_channels,
                        'categories': categories,
                        'total': len(guild.channels)
                    },
                    'roles': len(guild.roles),
                    'emojis': len(guild.emojis),
                    'stickers': len(guild.stickers),
                    'boosts': guild.premium_subscription_count,
                    'boostLevel': guild.premium_tier,
                    'createdAt': guild.created_at.isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise
    
    return {
        'guild.getInfo': get_info,
        'guild.getChannels': get_channels,
        'guild.getRoles': get_roles,
        'guild.getMembers': get_members,
        'guild.getMember': get_member,
        'guild.getEmojis': get_emojis,
        'guild.getStats': get_stats
    }
