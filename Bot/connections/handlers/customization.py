"""Customization module handlers for WebSocket"""

import logging
import re
from typing import Dict, Any
import disnake
from functions.database import database as db
from functions.utils import utils
import core

logger = logging.getLogger(__name__)

def register_customization_handlers():
    """Register all customization handlers"""
    
    # ============= STATUS HANDLERS =============
    
    async def get_status(bot, payload: dict) -> dict:
        """Get current bot status configuration"""
        try:
            status = db.get_document("custom_status") or {}
            
            # Get current bot status from config
            current_status = None
            if bot.user:
                current_status = {
                    'type': status.get('type', 'online'),
                    'names': status.get('names', []),
                    'bot_name': bot.user.name,
                    'bot_id': str(bot.user.id)
                }
                
                # Get current activities if bot has them
                if hasattr(bot, 'activities') and bot.activities:
                    current_status['activities'] = [
                        {
                            'name': activity.name,
                            'type': str(activity.type)
                        } for activity in bot.activities
                    ]
            
            return {
                'config': status,
                'current': current_status,
                'available_types': ['online', 'idle', 'dnd', 'streaming', 'offline']
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            raise
    
    async def update_status(bot, payload: dict) -> dict:
        """Update bot status configuration"""
        try:
            status_type = payload.get('type')
            names = payload.get('names', [])
            
            if not status_type:
                raise ValueError("status type is required")
            
            # Validate status type
            valid_types = ['online', 'idle', 'dnd', 'streaming', 'offline']
            if status_type not in valid_types:
                raise ValueError(f"Invalid status type. Must be one of: {', '.join(valid_types)}")
            
            # Get current config
            status = db.get_document("custom_status") or {}
            
            # Update configuration
            status['type'] = status_type
            
            if names:
                # Validate names (max 5)
                if len(names) > 5:
                    raise ValueError("Maximum 5 status names allowed")
                
                # Filter empty names
                status['names'] = [name.strip() for name in names if name and name.strip()]
                
                # Remove old 'name' field if exists
                if 'name' in status:
                    del status['name']
            
            # Save to database
            db.save_document("custom_status", {}, status)
            
            # Apply status change
            await core.change_status(bot)
            
            return {
                'success': True,
                'message': 'Status updated successfully',
                'config': status
            }
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            raise
    
    async def update_status_names(bot, payload: dict) -> dict:
        """Update only status names"""
        try:
            names = payload.get('names', [])
            
            if not isinstance(names, list):
                raise ValueError("names must be a list")
            
            # Validate names
            if len(names) > 5:
                raise ValueError("Maximum 5 status names allowed")
            
            # Get current config
            status = db.get_document("custom_status") or {}
            
            # Filter empty names
            status['names'] = [name.strip() for name in names if name and name.strip()]
            
            # Remove old 'name' field if exists
            if 'name' in status:
                del status['name']
            
            # Save to database
            db.save_document("custom_status", {}, status)
            
            # Apply status change
            await core.change_status(bot)
            
            return {
                'success': True,
                'message': 'Status names updated successfully',
                'names': status['names']
            }
        except Exception as e:
            logger.error(f"Error updating status names: {e}")
            raise
    
    # ============= COLORS HANDLERS =============
    
    async def get_colors(bot, payload: dict) -> dict:
        """Get custom colors configuration"""
        try:
            colors = db.get_document("custom_colors") or {}
            
            # Default colors if not set
            default_colors = {
                'primary': '#ffffff',
                'secondary': '#6c757d',
                'success': '#28a745',
                'danger': '#dc3545',
                'warning': '#ffc107'
            }
            
            # Merge with defaults
            for key, value in default_colors.items():
                if key not in colors:
                    colors[key] = value
            
            return {
                'colors': colors,
                'available_colors': list(default_colors.keys())
            }
        except Exception as e:
            logger.error(f"Error getting colors: {e}")
            raise
    
    async def update_colors(bot, payload: dict) -> dict:
        """Update custom colors"""
        try:
            colors = payload.get('colors', {})
            
            if not colors:
                raise ValueError("colors object is required")
            
            # Validate hex colors
            hex_pattern = re.compile(r'^#?([0-9a-fA-F]{6})$')
            
            validated_colors = {}
            for key, value in colors.items():
                if not value:
                    raise ValueError(f"Color value for {key} is required")
                
                if not hex_pattern.match(value):
                    raise ValueError(f"Invalid hex color for {key}: {value}. Use format #RRGGBB")
                
                # Normalize color
                normalized = utils.normalize_hex_color(value)
                if not normalized:
                    raise ValueError(f"Invalid color format for {key}: {value}")
                
                validated_colors[key] = normalized
            
            # Save to database
            db.save_document("custom_colors", {}, validated_colors)
            
            return {
                'success': True,
                'message': 'Colors updated successfully',
                'colors': validated_colors
            }
        except Exception as e:
            logger.error(f"Error updating colors: {e}")
            raise
    
    async def update_single_color(bot, payload: dict) -> dict:
        """Update a single color"""
        try:
            color_key = payload.get('key')
            color_value = payload.get('value')
            
            if not color_key or not color_value:
                raise ValueError("key and value are required")
            
            # Validate hex color
            hex_pattern = re.compile(r'^#?([0-9a-fA-F]{6})$')
            if not hex_pattern.match(color_value):
                raise ValueError(f"Invalid hex color: {color_value}. Use format #RRGGBB")
            
            # Normalize color
            normalized = utils.normalize_hex_color(color_value)
            if not normalized:
                raise ValueError(f"Invalid color format: {color_value}")
            
            # Get current colors
            colors = db.get_document("custom_colors") or {}
            colors[color_key] = normalized
            
            # Save to database
            db.save_document("custom_colors", {}, colors)
            
            return {
                'success': True,
                'message': f'Color {color_key} updated successfully',
                'key': color_key,
                'value': normalized
            }
        except Exception as e:
            logger.error(f"Error updating single color: {e}")
            raise
    
    # ============= MODE HANDLERS =============
    
    async def get_mode(bot, payload: dict) -> dict:
        """Get display mode (embed or components)"""
        try:
            mode_config = db.get_document("custom_mode") or {}
            mode = mode_config.get('mode', 'embed')
            
            return {
                'mode': mode,
                'available_modes': ['embed', 'components'],
                'description': {
                    'embed': 'Classic embed mode with traditional Discord embeds',
                    'components': 'Modern components v2 mode with containers'
                }
            }
        except Exception as e:
            logger.error(f"Error getting mode: {e}")
            raise
    
    async def update_mode(bot, payload: dict) -> dict:
        """Update display mode"""
        try:
            mode = payload.get('mode')
            
            if not mode:
                raise ValueError("mode is required")
            
            # Validate mode
            valid_modes = ['embed', 'components']
            if mode not in valid_modes:
                raise ValueError(f"Invalid mode. Must be one of: {', '.join(valid_modes)}")
            
            # Save to database
            db.save_document("custom_mode", {}, {'mode': mode})
            
            return {
                'success': True,
                'message': f'Display mode updated to {mode}',
                'mode': mode
            }
        except Exception as e:
            logger.error(f"Error updating mode: {e}")
            raise
    
    # ============= INFO HANDLERS =============
    
    async def get_info(bot, payload: dict) -> dict:
        """Get bot information configuration"""
        try:
            info = db.get_document("custom_info") or {}
            
            # Get current bot info
            current_info = {}
            if bot.user:
                current_info = {
                    'name': bot.user.name,
                    'discriminator': bot.user.discriminator,
                    'id': str(bot.user.id),
                    'avatar': str(bot.user.display_avatar.url) if bot.user.display_avatar else None,
                    'bot': bot.user.bot
                }
            
            return {
                'config': info,
                'current': current_info
            }
        except Exception as e:
            logger.error(f"Error getting info: {e}")
            raise
    
    async def update_info(bot, payload: dict) -> dict:
        """Update bot information"""
        try:
            info = payload.get('info', {})
            
            if not info:
                raise ValueError("info object is required")
            
            # Save to database
            db.save_document("custom_info", {}, info)
            
            # Note: Changing bot name/avatar requires Discord API calls
            # This just saves the configuration
            
            return {
                'success': True,
                'message': 'Bot information updated successfully',
                'info': info,
                'note': 'Some changes may require bot restart to take effect'
            }
        except Exception as e:
            logger.error(f"Error updating info: {e}")
            raise
    
    # ============= COMPLETE CONFIG HANDLERS =============
    
    async def get_all_config(bot, payload: dict) -> dict:
        """Get all customization configuration"""
        try:
            status = db.get_document("custom_status") or {}
            colors = db.get_document("custom_colors") or {}
            mode_config = db.get_document("custom_mode") or {}
            info = db.get_document("custom_info") or {}
            
            return {
                'status': status,
                'colors': colors,
                'mode': mode_config.get('mode', 'embed'),
                'info': info
            }
        except Exception as e:
            logger.error(f"Error getting all config: {e}")
            raise
    
    async def update_all_config(bot, payload: dict) -> dict:
        """Update all customization configuration"""
        try:
            config = payload.get('config', {})
            
            if not config:
                raise ValueError("config object is required")
            
            results = {}
            
            # Update status if provided
            if 'status' in config:
                db.save_document("custom_status", {}, config['status'])
                await core.change_status(bot)
                results['status'] = 'updated'
            
            # Update colors if provided
            if 'colors' in config:
                # Validate colors
                hex_pattern = re.compile(r'^#?([0-9a-fA-F]{6})$')
                validated_colors = {}
                
                for key, value in config['colors'].items():
                    if value and hex_pattern.match(value):
                        normalized = utils.normalize_hex_color(value)
                        if normalized:
                            validated_colors[key] = normalized
                
                if validated_colors:
                    db.save_document("custom_colors", {}, validated_colors)
                    results['colors'] = 'updated'
            
            # Update mode if provided
            if 'mode' in config:
                if config['mode'] in ['embed', 'components']:
                    db.save_document("custom_mode", {}, {'mode': config['mode']})
                    results['mode'] = 'updated'
            
            # Update info if provided
            if 'info' in config:
                db.save_document("custom_info", {}, config['info'])
                results['info'] = 'updated'
            
            return {
                'success': True,
                'message': 'Configuration updated successfully',
                'updated': results
            }
        except Exception as e:
            logger.error(f"Error updating all config: {e}")
            raise
    
    # ============= RESET HANDLERS =============
    
    async def reset_colors(bot, payload: dict) -> dict:
        """Reset colors to default"""
        try:
            default_colors = {
                'primary': '#ffffff',
                'secondary': '#6c757d',
                'success': '#28a745',
                'danger': '#dc3545',
                'warning': '#ffc107'
            }
            
            db.save_document("custom_colors", {}, default_colors)
            
            return {
                'success': True,
                'message': 'Colors reset to default',
                'colors': default_colors
            }
        except Exception as e:
            logger.error(f"Error resetting colors: {e}")
            raise
    
    async def reset_all(bot, payload: dict) -> dict:
        """Reset all customization to default"""
        try:
            # Reset status
            default_status = {
                'type': 'online',
                'names': []
            }
            db.save_document("custom_status", {}, default_status)
            
            # Reset colors
            default_colors = {
                'primary': '#ffffff',
                'secondary': '#6c757d',
                'success': '#28a745',
                'danger': '#dc3545',
                'warning': '#ffc107'
            }
            db.save_document("custom_colors", {}, default_colors)
            
            # Reset mode
            db.save_document("custom_mode", {}, {'mode': 'embed'})
            
            # Reset info
            db.save_document("custom_info", {}, {})
            
            # Apply changes
            await core.change_status(bot)
            
            return {
                'success': True,
                'message': 'All customization reset to default',
                'config': {
                    'status': default_status,
                    'colors': default_colors,
                    'mode': 'embed',
                    'info': {}
                }
            }
        except Exception as e:
            logger.error(f"Error resetting all: {e}")
            raise
    
    return {
        # Status
        'customization.getStatus': get_status,
        'customization.updateStatus': update_status,
        'customization.updateStatusNames': update_status_names,
        
        # Colors
        'customization.getColors': get_colors,
        'customization.updateColors': update_colors,
        'customization.updateSingleColor': update_single_color,
        'customization.resetColors': reset_colors,
        
        # Mode
        'customization.getMode': get_mode,
        'customization.updateMode': update_mode,
        
        # Info
        'customization.getInfo': get_info,
        'customization.updateInfo': update_info,
        
        # Complete config
        'customization.getAllConfig': get_all_config,
        'customization.updateAllConfig': update_all_config,
        'customization.resetAll': reset_all
    }
