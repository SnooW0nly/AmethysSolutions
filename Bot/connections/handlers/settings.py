"""Settings module handlers for WebSocket"""

import logging
from typing import Dict, Any
import disnake
from functions.database import database as db

logger = logging.getLogger(__name__)

# Import role and channel options
from modules.settings.cargos.listar import CARGOS_OPCOES, CARGOS_CORES
from modules.settings.canais.listar import CANAIS_OPCOES

def register_settings_handlers():
    """Register all settings handlers"""
    
    # ============= ROLES (CARGOS) HANDLERS =============
    
    async def get_roles(bot, payload: dict) -> dict:
        """Get all configured roles"""
        try:
            cargos = db.get_document("cargos") or {}
            
            # Get guild for role validation
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            roles_data = []
            for cargo_key, cargo_name, emoji in CARGOS_OPCOES:
                role_id = cargos.get(cargo_key)
                role_obj = None
                
                if role_id and guild:
                    try:
                        role_obj = guild.get_role(int(role_id))
                    except:
                        pass
                
                roles_data.append({
                    'key': cargo_key,
                    'name': cargo_name,
                    'role_id': role_id,
                    'role_name': role_obj.name if role_obj else None,
                    'role_color': str(role_obj.color) if role_obj else None,
                    'configured': role_obj is not None
                })
            
            return {
                'roles': roles_data,
                'count': len(roles_data),
                'configured_count': sum(1 for r in roles_data if r['configured'])
            }
        except Exception as e:
            logger.error(f"Error getting roles: {e}")
            raise
    
    async def get_role(bot, payload: dict) -> dict:
        """Get specific role configuration"""
        try:
            role_key = payload.get('role_key')
            
            if not role_key:
                raise ValueError("role_key is required")
            
            cargos = db.get_document("cargos") or {}
            role_id = cargos.get(role_key)
            
            # Get guild
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            role_obj = None
            if role_id and guild:
                try:
                    role_obj = guild.get_role(int(role_id))
                except:
                    pass
            
            # Find role info
            role_info = next((r for r in CARGOS_OPCOES if r[0] == role_key), None)
            if not role_info:
                raise ValueError(f"Role key {role_key} not found")
            
            return {
                'key': role_key,
                'name': role_info[1],
                'role_id': role_id,
                'role_name': role_obj.name if role_obj else None,
                'role_color': str(role_obj.color) if role_obj else None,
                'role_position': role_obj.position if role_obj else None,
                'role_members': len(role_obj.members) if role_obj else 0,
                'configured': role_obj is not None
            }
        except Exception as e:
            logger.error(f"Error getting role: {e}")
            raise
    
    async def update_role(bot, payload: dict) -> dict:
        """Update role configuration"""
        try:
            role_key = payload.get('role_key')
            role_id = payload.get('role_id')
            
            if not role_key:
                raise ValueError("role_key is required")
            
            # Validate role exists if provided
            if role_id:
                import json
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                guild_id = int(config.get('bot', {}).get('server'))
                guild = bot.get_guild(guild_id)
                
                if not guild:
                    raise ValueError("Guild not found")
                
                role = guild.get_role(int(role_id))
                if not role:
                    raise ValueError(f"Role {role_id} not found")
            
            # Get current config
            cargos = db.get_document("cargos") or {}
            
            # Update role
            if role_id:
                cargos[role_key] = role_id
            else:
                # Remove role if None
                if role_key in cargos:
                    del cargos[role_key]
            
            # Save
            db.save_document("cargos", {}, cargos)
            
            return {
                'success': True,
                'message': f'Role {role_key} updated successfully',
                'role_key': role_key,
                'role_id': role_id
            }
        except Exception as e:
            logger.error(f"Error updating role: {e}")
            raise
    
    async def create_role(bot, payload: dict) -> dict:
        """Create a new role"""
        try:
            role_key = payload.get('role_key')
            role_name = payload.get('role_name')
            role_color = payload.get('role_color')
            
            if not role_key:
                raise ValueError("role_key is required")
            
            # Get guild
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            # Get role info
            role_info = next((r for r in CARGOS_OPCOES if r[0] == role_key), None)
            if not role_info:
                raise ValueError(f"Role key {role_key} not found")
            
            # Use provided name or default
            if not role_name:
                role_name = role_info[1]
            
            # Use provided color or random from CARGOS_CORES
            if role_color:
                try:
                    color = disnake.Color(int(role_color.replace('#', ''), 16) if isinstance(role_color, str) else role_color)
                except:
                    import random
                    color = disnake.Color(random.choice(CARGOS_CORES))
            else:
                import random
                color = disnake.Color(random.choice(CARGOS_CORES))
            
            # Create role
            new_role = await guild.create_role(
                name=role_name,
                color=color,
                reason=f"Created via WebSocket API for {role_key}"
            )
            
            # Save to database
            cargos = db.get_document("cargos") or {}
            cargos[role_key] = str(new_role.id)
            db.save_document("cargos", {}, cargos)
            
            return {
                'success': True,
                'message': f'Role created successfully',
                'role_key': role_key,
                'role_id': str(new_role.id),
                'role_name': new_role.name,
                'role_color': str(new_role.color)
            }
        except Exception as e:
            logger.error(f"Error creating role: {e}")
            raise
    
    async def delete_role_config(bot, payload: dict) -> dict:
        """Delete role configuration (not the role itself)"""
        try:
            role_key = payload.get('role_key')
            
            if not role_key:
                raise ValueError("role_key is required")
            
            # Get current config
            cargos = db.get_document("cargos") or {}
            
            if role_key not in cargos:
                raise ValueError(f"Role {role_key} not configured")
            
            # Remove from config
            del cargos[role_key]
            
            # Save
            db.save_document("cargos", {}, cargos)
            
            return {
                'success': True,
                'message': f'Role configuration deleted',
                'role_key': role_key
            }
        except Exception as e:
            logger.error(f"Error deleting role config: {e}")
            raise
    
    # ============= CHANNELS (CANAIS) HANDLERS =============
    
    async def get_channels(bot, payload: dict) -> dict:
        """Get all configured channels"""
        try:
            canais = db.get_document("canais") or {}
            
            # Get guild
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            channels_data = []
            for canal_key, canal_name, emoji in CANAIS_OPCOES:
                channel_id = canais.get(canal_key)
                channel_obj = None
                
                if channel_id and guild:
                    try:
                        channel_obj = guild.get_channel(int(channel_id))
                    except:
                        pass
                
                channels_data.append({
                    'key': canal_key,
                    'name': canal_name,
                    'channel_id': channel_id,
                    'channel_name': channel_obj.name if channel_obj else None,
                    'channel_type': str(channel_obj.type) if channel_obj else None,
                    'configured': channel_obj is not None
                })
            
            return {
                'channels': channels_data,
                'count': len(channels_data),
                'configured_count': sum(1 for c in channels_data if c['configured'])
            }
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            raise
    
    async def get_channel(bot, payload: dict) -> dict:
        """Get specific channel configuration"""
        try:
            channel_key = payload.get('channel_key')
            
            if not channel_key:
                raise ValueError("channel_key is required")
            
            canais = db.get_document("canais") or {}
            channel_id = canais.get(channel_key)
            
            # Get guild
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            channel_obj = None
            if channel_id and guild:
                try:
                    channel_obj = guild.get_channel(int(channel_id))
                except:
                    pass
            
            # Find channel info
            channel_info = next((c for c in CANAIS_OPCOES if c[0] == channel_key), None)
            if not channel_info:
                raise ValueError(f"Channel key {channel_key} not found")
            
            return {
                'key': channel_key,
                'name': channel_info[1],
                'channel_id': channel_id,
                'channel_name': channel_obj.name if channel_obj else None,
                'channel_type': str(channel_obj.type) if channel_obj else None,
                'channel_category': channel_obj.category.name if channel_obj and channel_obj.category else None,
                'configured': channel_obj is not None
            }
        except Exception as e:
            logger.error(f"Error getting channel: {e}")
            raise
    
    async def update_channel(bot, payload: dict) -> dict:
        """Update channel configuration"""
        try:
            channel_key = payload.get('channel_key')
            channel_id = payload.get('channel_id')
            
            if not channel_key:
                raise ValueError("channel_key is required")
            
            # Validate channel exists if provided
            if channel_id:
                import json
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                guild_id = int(config.get('bot', {}).get('server'))
                guild = bot.get_guild(guild_id)
                
                if not guild:
                    raise ValueError("Guild not found")
                
                channel = guild.get_channel(int(channel_id))
                if not channel:
                    raise ValueError(f"Channel {channel_id} not found")
            
            # Get current config
            canais = db.get_document("canais") or {}
            
            # Update channel
            if channel_id:
                canais[channel_key] = channel_id
            else:
                # Remove channel if None
                if channel_key in canais:
                    del canais[channel_key]
            
            # Save
            db.save_document("canais", {}, canais)
            
            return {
                'success': True,
                'message': f'Channel {channel_key} updated successfully',
                'channel_key': channel_key,
                'channel_id': channel_id
            }
        except Exception as e:
            logger.error(f"Error updating channel: {e}")
            raise
    
    async def create_channel(bot, payload: dict) -> dict:
        """Create a new channel"""
        try:
            channel_key = payload.get('channel_key')
            channel_name = payload.get('channel_name')
            category_id = payload.get('category_id')
            
            if not channel_key:
                raise ValueError("channel_key is required")
            
            # Get guild
            import json
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            guild_id = int(config.get('bot', {}).get('server'))
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            # Get channel info
            channel_info = next((c for c in CANAIS_OPCOES if c[0] == channel_key), None)
            if not channel_info:
                raise ValueError(f"Channel key {channel_key} not found")
            
            # Use provided name or default
            if not channel_name:
                channel_name = channel_info[1].lower().replace(' ', '-')
            
            # Get category if provided
            category = None
            if category_id:
                category = guild.get_channel(int(category_id))
            
            # Create channel
            new_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                reason=f"Created via WebSocket API for {channel_key}"
            )
            
            # Save to database
            canais = db.get_document("canais") or {}
            canais[channel_key] = str(new_channel.id)
            db.save_document("canais", {}, canais)
            
            return {
                'success': True,
                'message': f'Channel created successfully',
                'channel_key': channel_key,
                'channel_id': str(new_channel.id),
                'channel_name': new_channel.name
            }
        except Exception as e:
            logger.error(f"Error creating channel: {e}")
            raise
    
    async def delete_channel_config(bot, payload: dict) -> dict:
        """Delete channel configuration (not the channel itself)"""
        try:
            channel_key = payload.get('channel_key')
            
            if not channel_key:
                raise ValueError("channel_key is required")
            
            # Get current config
            canais = db.get_document("canais") or {}
            
            if channel_key not in canais:
                raise ValueError(f"Channel {channel_key} not configured")
            
            # Remove from config
            del canais[channel_key]
            
            # Save
            db.save_document("canais", {}, canais)
            
            return {
                'success': True,
                'message': f'Channel configuration deleted',
                'channel_key': channel_key
            }
        except Exception as e:
            logger.error(f"Error deleting channel config: {e}")
            raise
    
    # ============= PAYMENTS HANDLERS =============
    
    async def get_payment_methods(bot, payload: dict) -> dict:
        """Get payment methods configuration"""
        try:
            payment_configs = db.get_document("payment_configs") or {}
            pagamentos = db.get_document("pagamentos") or {}
            
            methods = []
            for method, config in payment_configs.items():
                methods.append({
                    'method': method,
                    'enabled': pagamentos.get(method, False),
                    'configured': bool(config),
                    'config': config if config else {}
                })
            
            return {
                'methods': methods,
                'count': len(methods),
                'enabled_count': sum(1 for m in methods if m['enabled'])
            }
        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            raise
    
    async def update_payment_method(bot, payload: dict) -> dict:
        """Update payment method configuration"""
        try:
            method = payload.get('method')
            config = payload.get('config')
            enabled = payload.get('enabled')
            
            if not method:
                raise ValueError("method is required")
            
            # Update config if provided
            if config is not None:
                payment_configs = db.get_document("payment_configs") or {}
                payment_configs[method] = config
                db.save_document("payment_configs", {}, payment_configs)
            
            # Update enabled status if provided
            if enabled is not None:
                pagamentos = db.get_document("pagamentos") or {}
                pagamentos[method] = enabled
                db.save_document("pagamentos", {}, pagamentos)
            
            return {
                'success': True,
                'message': f'Payment method {method} updated',
                'method': method,
                'enabled': enabled
            }
        except Exception as e:
            logger.error(f"Error updating payment method: {e}")
            raise
    
    # ============= GENERAL SETTINGS =============
    
    async def get_all_settings(bot, payload: dict) -> dict:
        """Get all settings"""
        try:
            cargos = db.get_document("cargos") or {}
            canais = db.get_document("canais") or {}
            payment_configs = db.get_document("payment_configs") or {}
            pagamentos = db.get_document("pagamentos") or {}
            
            return {
                'roles': cargos,
                'channels': canais,
                'payment_configs': payment_configs,
                'payment_status': pagamentos
            }
        except Exception as e:
            logger.error(f"Error getting all settings: {e}")
            raise
    
    return {
        # Roles
        'settings.getRoles': get_roles,
        'settings.getRole': get_role,
        'settings.updateRole': update_role,
        'settings.createRole': create_role,
        'settings.deleteRoleConfig': delete_role_config,
        
        # Channels
        'settings.getChannels': get_channels,
        'settings.getChannel': get_channel,
        'settings.updateChannel': update_channel,
        'settings.createChannel': create_channel,
        'settings.deleteChannelConfig': delete_channel_config,
        
        # Payments
        'settings.getPaymentMethods': get_payment_methods,
        'settings.updatePaymentMethod': update_payment_method,
        
        # General
        'settings.getAllSettings': get_all_settings
    }
