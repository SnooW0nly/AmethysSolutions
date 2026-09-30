"""Cloud module handlers for WebSocket

Handlers que usam as funções REAIS do módulo Cloud do bot:
- websocket_manager.py para gifts (via Sync Cloud API)
- task_manager.py para tasks (gerenciamento local)
"""

import logging
from typing import Dict, Any
import disnake
from functions.database import database as db

logger = logging.getLogger(__name__)

def register_cloud_handlers():
    """Register all cloud-related handlers using real bot functions"""
    
    # ============= CONFIGURATION HANDLERS =============
    
    async def get_config(bot, payload: dict) -> dict:
        """Get Sync Cloud configuration"""
        try:
            cloud_config = db.obter("database/cloud/data.json") or {}
            
            # Get verified role
            verified_role_id = db.get_document("cargos").get("cargo_verificado")
            
            # Get log channel
            log_channel_id = cloud_config.get("log_channel_id")
            
            # Check if configured
            is_configured = bool(cloud_config.get("client_id"))
            
            # Get WebSocket status
            ws_status = 'disconnected'
            try:
                from modules.cloud.update_api import get_websocket_manager
                ws_manager = get_websocket_manager()
                if ws_manager.is_connected():
                    ws_status = 'connected'
            except:
                pass
            
            return {
                'config': {
                    'client_id': cloud_config.get('client_id'),
                    'client_secret': cloud_config.get('client_secret'),
                    'log_channel_id': log_channel_id,
                    'verified_role_id': verified_role_id
                },
                'is_configured': is_configured,
                'websocket_status': ws_status
            }
        except Exception as e:
            logger.error(f"Error getting cloud config: {e}")
            raise
    
    async def update_credentials(bot, payload: dict) -> dict:
        """Update Sync Cloud credentials"""
        try:
            client_id = payload.get('client_id')
            client_secret = payload.get('client_secret')
            
            if not client_id or not client_secret:
                raise ValueError("client_id and client_secret are required")
            
            # Get current config
            cloud_config = db.obter("database/cloud/data.json") or {}
            
            # Update credentials
            cloud_config['client_id'] = client_id
            cloud_config['client_secret'] = client_secret
            
            # Save to database
            db.salvar("database/cloud/data.json", cloud_config)
            
            # Try to connect WebSocket
            try:
                from modules.cloud.update_api import get_websocket_manager
                ws_manager = get_websocket_manager()
                
                if not ws_manager.is_connected():
                    await ws_manager.start()
                    
            except Exception as e:
                logger.warning(f"Could not start WebSocket after credential update: {e}")
            
            return {
                'success': True,
                'message': 'Credentials updated successfully',
                'is_configured': True
            }
        except Exception as e:
            logger.error(f"Error updating credentials: {e}")
            raise
    
    async def update_log_channel(bot, payload: dict) -> dict:
        """Update log channel for Sync Cloud"""
        try:
            channel_id = payload.get('channel_id')
            
            if not channel_id:
                raise ValueError("channel_id is required")
            
            # Validate channel exists
            try:
                channel = bot.get_channel(int(channel_id))
                if not channel:
                    raise ValueError(f"Channel {channel_id} not found")
            except ValueError as e:
                if "not found" in str(e):
                    raise
                raise ValueError(f"Invalid channel ID: {channel_id}")
            
            # Get current config
            cloud_config = db.obter("database/cloud/data.json") or {}
            
            # Update log channel
            cloud_config['log_channel_id'] = str(channel_id)
            
            # Save to database
            db.salvar("database/cloud/data.json", cloud_config)
            
            return {
                'success': True,
                'message': 'Log channel updated successfully',
                'channel_id': channel_id,
                'channel_name': channel.name
            }
        except Exception as e:
            logger.error(f"Error updating log channel: {e}")
            raise
    
    async def update_verified_role(bot, payload: dict) -> dict:
        """Update verified role for Sync Cloud"""
        try:
            role_id = payload.get('role_id')
            
            if not role_id:
                raise ValueError("role_id is required")
            
            # Get guild
            from functions.utils import utils
            guild_id = utils.obter_server_principal()
            guild = bot.get_guild(guild_id)
            
            if not guild:
                raise ValueError("Guild not found")
            
            # Validate role exists
            role = guild.get_role(int(role_id))
            if not role:
                raise ValueError(f"Role {role_id} not found")
            
            # Update in cargos document
            cargos = db.get_document("cargos") or {}
            cargos['cargo_verificado'] = str(role_id)
            db.save_document("cargos", {}, cargos)
            
            return {
                'success': True,
                'message': 'Verified role updated successfully',
                'role_id': role_id,
                'role_name': role.name
            }
        except Exception as e:
            logger.error(f"Error updating verified role: {e}")
            raise
    
    # ============= STATISTICS HANDLERS =============
    
    async def get_stats(bot, payload: dict) -> dict:
        """Get Sync Cloud statistics"""
        try:
            cloud_config = db.obter("database/cloud/data.json") or {}
            client_id = cloud_config.get("client_id")
            
            verified_count = 0
            ws_connected = False
            
            if client_id:
                try:
                    from modules.cloud.update_api import get_websocket_manager
                    ws_manager = get_websocket_manager()
                    ws_connected = ws_manager.is_connected()
                    
                    if ws_connected:
                        # Get auth count from Sync Cloud API
                        response = await ws_manager.check_auth_count(client_id)
                        if response.get("success"):
                            verified_count = response.get("data", {}).get("authCount", 0)
                except Exception as e:
                    logger.error(f"Error getting auth count: {e}")
            
            return {
                'verified_members': verified_count,
                'websocket_connected': ws_connected,
                'is_configured': bool(client_id)
            }
        except Exception as e:
            logger.error(f"Error getting cloud stats: {e}")
            raise
    
    async def get_auth_logs(bot, payload: dict) -> dict:
        """Get authentication logs"""
        try:
            limit = payload.get('limit', 50)
            
            # Get logs from database
            auth_logs = db.obter("database/cloud/auth_logs.json") or []
            
            # Sort by timestamp (newest first) and limit
            sorted_logs = sorted(auth_logs, key=lambda x: x.get('timestamp', ''), reverse=True)
            limited_logs = sorted_logs[:limit]
            
            return {
                'logs': limited_logs,
                'count': len(limited_logs),
                'total': len(auth_logs)
            }
        except Exception as e:
            logger.error(f"Error getting auth logs: {e}")
            raise
    
    # ============= GIFTS HANDLERS (via Sync Cloud API) =============
    
    async def get_gifts(bot, payload: dict) -> dict:
        """Get all gifts from Sync Cloud API"""
        try:
            cloud_config = db.obter("database/cloud/data.json") or {}
            client_id = cloud_config.get("client_id")
            
            if not client_id:
                raise ValueError("Cloud not configured. Please set credentials first.")
            
            from modules.cloud.update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            if not ws_manager.is_connected():
                raise ValueError("WebSocket not connected to Sync Cloud")
            
            # Get gifts from Sync Cloud API
            response = await ws_manager.get_gifts(client_id)
            
            if not response.get("success"):
                raise ValueError(response.get("message", "Failed to get gifts"))
            
            gifts_data = response.get("data", {})
            gifts_list = gifts_data.get("gifts", [])
            
            return {
                'gifts': gifts_list,
                'count': len(gifts_list)
            }
        except Exception as e:
            logger.error(f"Error getting gifts: {e}")
            raise
    
    async def get_gift(bot, payload: dict) -> dict:
        """Get specific gift from Sync Cloud API"""
        try:
            gift_id = payload.get('gift_id')
            
            if not gift_id:
                raise ValueError("gift_id is required")
            
            # Get all gifts and find the specific one
            all_gifts = await get_gifts(bot, {})
            
            gift = next((g for g in all_gifts['gifts'] if g.get('id') == gift_id), None)
            
            if not gift:
                raise ValueError(f"Gift {gift_id} not found")
            
            return {'gift': gift}
        except Exception as e:
            logger.error(f"Error getting gift: {e}")
            raise
    
    async def create_gift(bot, payload: dict) -> dict:
        """Create new gift via Sync Cloud API"""
        try:
            gift_data = payload.get('gift_data')
            
            if not gift_data:
                raise ValueError("gift_data is required")
            
            # Validate required fields
            if not gift_data.get('name'):
                raise ValueError("Gift name is required")
            
            if not gift_data.get('members_count'):
                raise ValueError("members_count is required")
            
            cloud_config = db.obter("database/cloud/data.json") or {}
            client_id = cloud_config.get("client_id")
            
            if not client_id:
                raise ValueError("Cloud not configured")
            
            from modules.cloud.update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            if not ws_manager.is_connected():
                raise ValueError("WebSocket not connected")
            
            # Prepare gift data for API
            api_gift_data = {
                'name': gift_data['name'],
                'membersCount': int(gift_data['members_count']),
                'roleId': gift_data.get('role_id'),
                'type': gift_data.get('type', 'role')
            }
            
            # Create gift via Sync Cloud API
            response = await ws_manager.send_gift(client_id, api_gift_data)
            
            if not response.get("success"):
                raise ValueError(response.get("message", "Failed to create gift"))
            
            gift_info = response.get("data", {})
            
            return {
                'success': True,
                'message': 'Gift created successfully',
                'gift': gift_info
            }
        except Exception as e:
            logger.error(f"Error creating gift: {e}")
            raise
    
    async def update_gift(bot, payload: dict) -> dict:
        """Update gift via Sync Cloud API"""
        try:
            gift_id = payload.get('gift_id')
            gift_data = payload.get('gift_data')
            
            if not gift_id:
                raise ValueError("gift_id is required")
            
            if not gift_data:
                raise ValueError("gift_data is required")
            
            cloud_config = db.obter("database/cloud/data.json") or {}
            client_id = cloud_config.get("client_id")
            
            if not client_id:
                raise ValueError("Cloud not configured")
            
            from modules.cloud.update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            if not ws_manager.is_connected():
                raise ValueError("WebSocket not connected")
            
            # Prepare update data
            update_data = {
                'botId': client_id,
                'giftId': gift_id,
                'updates': {}
            }
            
            # Add fields to update
            if 'name' in gift_data:
                update_data['updates']['name'] = gift_data['name']
            if 'members_count' in gift_data:
                update_data['updates']['membersCount'] = int(gift_data['members_count'])
            if 'role_id' in gift_data:
                update_data['updates']['roleId'] = gift_data['role_id']
            
            # Update gift via Sync Cloud API
            response = await ws_manager.update_gift(update_data)
            
            if not response.get("success"):
                raise ValueError(response.get("message", "Failed to update gift"))
            
            return {
                'success': True,
                'message': 'Gift updated successfully',
                'gift': response.get("data", {})
            }
        except Exception as e:
            logger.error(f"Error updating gift: {e}")
            raise
    
    async def delete_gift(bot, payload: dict) -> dict:
        """Delete gift via Sync Cloud API"""
        try:
            gift_id = payload.get('gift_id')
            
            if not gift_id:
                raise ValueError("gift_id is required")
            
            cloud_config = db.obter("database/cloud/data.json") or {}
            client_id = cloud_config.get("client_id")
            
            if not client_id:
                raise ValueError("Cloud not configured")
            
            from modules.cloud.update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            if not ws_manager.is_connected():
                raise ValueError("WebSocket not connected")
            
            # Delete gift via Sync Cloud API
            delete_data = {
                'botId': client_id,
                'giftId': gift_id
            }
            
            response = await ws_manager.delete_gift(delete_data)
            
            if not response.get("success"):
                raise ValueError(response.get("message", "Failed to delete gift"))
            
            return {
                'success': True,
                'message': 'Gift deleted successfully'
            }
        except Exception as e:
            logger.error(f"Error deleting gift: {e}")
            raise
    
    # ============= TASKS HANDLERS (local task_manager) =============
    
    async def get_tasks(bot, payload: dict) -> dict:
        """Get all tasks from local task manager"""
        try:
            from modules.cloud.task_manager import get_all_tasks
            
            tasks = get_all_tasks()
            
            return {
                'tasks': tasks,
                'count': len(tasks)
            }
        except Exception as e:
            logger.error(f"Error getting tasks: {e}")
            raise
    
    async def get_task(bot, payload: dict) -> dict:
        """Get specific task"""
        try:
            task_id = payload.get('task_id')
            
            if not task_id:
                raise ValueError("task_id is required")
            
            from modules.cloud.task_manager import get_task
            
            task = get_task(task_id)
            
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            return {'task': task}
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            raise
    
    async def create_task(bot, payload: dict) -> dict:
        """Create new task"""
        try:
            task_data = payload.get('task_data')
            
            if not task_data:
                raise ValueError("task_data is required")
            
            # Validate required fields
            task_type = task_data.get('type')
            if not task_type:
                raise ValueError("Task type is required")
            
            user_id = task_data.get('user_id', 'system')
            user_name = task_data.get('user_name', 'System')
            
            from modules.cloud.task_manager import create_task
            
            # Create task
            task_id = create_task(
                task_type=task_type,
                user_id=user_id,
                user_name=user_name,
                data=task_data.get('data', {})
            )
            
            if not task_id:
                raise ValueError("Failed to create task")
            
            return {
                'success': True,
                'message': 'Task created successfully',
                'task_id': task_id
            }
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    async def update_task(bot, payload: dict) -> dict:
        """Update task status"""
        try:
            task_id = payload.get('task_id')
            status = payload.get('status')
            
            if not task_id:
                raise ValueError("task_id is required")
            
            if not status:
                raise ValueError("status is required")
            
            from modules.cloud.task_manager import update_task_status
            
            # Update task
            success = update_task_status(
                task_id=task_id,
                status=status,
                data=payload.get('data', {})
            )
            
            if not success:
                raise ValueError("Failed to update task")
            
            return {
                'success': True,
                'message': 'Task updated successfully'
            }
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            raise
    
    async def delete_task(bot, payload: dict) -> dict:
        """Delete task"""
        try:
            task_id = payload.get('task_id')
            
            if not task_id:
                raise ValueError("task_id is required")
            
            from modules.cloud.task_manager import delete_task
            
            # Delete task
            success = delete_task(task_id)
            
            if not success:
                raise ValueError("Failed to delete task")
            
            return {
                'success': True,
                'message': 'Task deleted successfully'
            }
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            raise
    
    # ============= VERIFICATION MESSAGE =============
    
    def _clean_invalid_urls(config_dict: dict, url_keys: list) -> dict:
        """Helper to clean invalid URLs from config"""
        for key in url_keys:
            if key in config_dict:
                value = config_dict[key]
                # Remove if not a valid URL
                if not value or not str(value).strip():
                    config_dict.pop(key, None)
                elif not (str(value).strip().startswith('http://') or str(value).strip().startswith('https://')):
                    config_dict.pop(key, None)
        return config_dict
    
    async def get_verification_message(bot, payload: dict) -> dict:
        """Get verification message configuration"""
        try:
            cloud_config = db.obter("database/cloud/data.json") or {}
            message_config = cloud_config.get("message_verify", {})
            
            style = message_config.get("message_style", "embed")
            button_data = message_config.get("button", {})
            
            # Get content based on style and clean invalid URLs
            content_data = {}
            if style == "embed":
                content_data = message_config.get("embed", {})
                _clean_invalid_urls(content_data, ['image_url', 'thumbnail_url'])
            elif style == "content":
                content_data = message_config.get("content", {})
                _clean_invalid_urls(content_data, ['image_url'])
            elif style == "container":
                content_data = message_config.get("container", {})
                _clean_invalid_urls(content_data, ['image_url', 'thumbnail_url'])
            
            # Save cleaned config back to database
            if message_config:
                db.salvar("database/cloud/data.json", cloud_config)
            
            return {
                'style': style,
                'button': button_data,
                'content': content_data,
                'configured': bool(button_data.get('label')) and bool(content_data)
            }
        except Exception as e:
            logger.error(f"Error getting verification message: {e}")
            raise
    
    async def update_verification_message(bot, payload: dict) -> dict:
        """Update verification message configuration"""
        try:
            update_type = payload.get('update_type')  # 'button', 'content'
            data = payload.get('data')
            
            if not update_type or not data:
                raise ValueError("update_type and data are required")
            
            cloud_config = db.obter("database/cloud/data.json") or {}
            
            if "message_verify" not in cloud_config:
                cloud_config["message_verify"] = {}
            
            message_config = cloud_config["message_verify"]
            style = message_config.get("message_style", "embed")
            
            if update_type == "button":
                # Update button configuration
                if "button" not in message_config:
                    message_config["button"] = {}
                
                # Map style names
                style_map = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
                if 'style' in data and data['style'] in style_map:
                    data['style'] = style_map[data['style']]
                
                message_config["button"].update(data)
                
            elif update_type == "content":
                # Helper function to check if value is valid
                def is_valid_value(value):
                    if not value:
                        return False
                    str_value = str(value).strip()
                    if not str_value:
                        return False
                    # Check if it's a valid URL for image fields
                    if len(str_value) < 3 or str_value in ['a', 'aa', 'aaa']:
                        return False
                    return True
                
                # Clean empty/invalid values from data
                cleaned_data = {}
                for k, v in data.items():
                    if k in ['image_url', 'thumbnail_url']:
                        # For URLs, validate they start with http
                        if v and str(v).strip() and (str(v).strip().startswith('http://') or str(v).strip().startswith('https://')):
                            cleaned_data[k] = v
                    elif is_valid_value(v):
                        cleaned_data[k] = v
                
                # Update content based on current style
                if style == "embed":
                    if "embed" not in message_config:
                        message_config["embed"] = {}
                    # Remove empty/invalid fields
                    for key in ['image_url', 'thumbnail_url', 'color', 'description']:
                        if key in data:
                            value = data[key]
                            if key in ['image_url', 'thumbnail_url']:
                                # Remove if not a valid URL
                                if not value or not str(value).strip() or not (str(value).strip().startswith('http://') or str(value).strip().startswith('https://')):
                                    message_config["embed"].pop(key, None)
                            elif not is_valid_value(value):
                                message_config["embed"].pop(key, None)
                    # Update with cleaned data
                    message_config["embed"].update(cleaned_data)
                    
                elif style == "content":
                    if "content" not in message_config:
                        message_config["content"] = {}
                    # Remove empty/invalid fields
                    for key in ['image_url', 'content']:
                        if key in data:
                            value = data[key]
                            if key == 'image_url':
                                # Remove if not a valid URL
                                if not value or not str(value).strip() or not (str(value).strip().startswith('http://') or str(value).strip().startswith('https://')):
                                    message_config["content"].pop(key, None)
                            elif not is_valid_value(value):
                                message_config["content"].pop(key, None)
                    # Update with cleaned data
                    message_config["content"].update(cleaned_data)
                    
                elif style == "container":
                    if "container" not in message_config:
                        message_config["container"] = {}
                    # Remove empty/invalid fields
                    for key in ['image_url', 'thumbnail_url', 'color', 'content']:
                        if key in data:
                            value = data[key]
                            if key in ['image_url', 'thumbnail_url']:
                                # Remove if not a valid URL
                                if not value or not str(value).strip() or not (str(value).strip().startswith('http://') or str(value).strip().startswith('https://')):
                                    message_config["container"].pop(key, None)
                            elif not is_valid_value(value):
                                message_config["container"].pop(key, None)
                    # Update with cleaned data
                    message_config["container"].update(cleaned_data)
            
            # Save to database
            db.salvar("database/cloud/data.json", cloud_config)
            
            return {
                'success': True,
                'message': f'{update_type.capitalize()} updated successfully',
                'style': style
            }
        except Exception as e:
            logger.error(f"Error updating verification message: {e}")
            raise
    
    async def update_message_style(bot, payload: dict) -> dict:
        """Update verification message style (embed/content/container)"""
        try:
            style = payload.get('style')
            
            if not style:
                raise ValueError("style is required")
            
            valid_styles = ['embed', 'content', 'container']
            if style not in valid_styles:
                raise ValueError(f"Invalid style. Must be one of: {', '.join(valid_styles)}")
            
            cloud_config = db.obter("database/cloud/data.json") or {}
            
            if "message_verify" not in cloud_config:
                cloud_config["message_verify"] = {}
            
            cloud_config["message_verify"]["message_style"] = style
            
            # Save to database
            db.salvar("database/cloud/data.json", cloud_config)
            
            return {
                'success': True,
                'message': f'Message style updated to {style}',
                'style': style
            }
        except Exception as e:
            logger.error(f"Error updating message style: {e}")
            raise
    
    async def reset_verification_message(bot, payload: dict) -> dict:
        """Reset verification message configuration
        
        Args:
            reset_type: 'all', 'button', 'embed', 'content', 'container'
        """
        try:
            reset_type = payload.get('reset_type', 'all')
            
            valid_types = ['all', 'button', 'embed', 'content', 'container']
            if reset_type not in valid_types:
                raise ValueError(f"Invalid reset_type. Must be one of: {', '.join(valid_types)}")
            
            cloud_config = db.obter("database/cloud/data.json") or {}
            
            if "message_verify" not in cloud_config:
                cloud_config["message_verify"] = {}
            
            message_config = cloud_config["message_verify"]
            
            # Reset based on type
            if reset_type == 'all':
                # Reset everything
                cloud_config["message_verify"] = {
                    "message_style": "embed"
                }
                reset_items = ['button', 'embed', 'content', 'container']
                
            elif reset_type == 'button':
                # Reset only button
                message_config.pop('button', None)
                reset_items = ['button']
                
            elif reset_type in ['embed', 'content', 'container']:
                # Reset specific content style
                message_config.pop(reset_type, None)
                reset_items = [reset_type]
            
            # Save to database
            db.salvar("database/cloud/data.json", cloud_config)
            
            return {
                'success': True,
                'message': f'Reset {", ".join(reset_items)} successfully',
                'reset_type': reset_type,
                'reset_items': reset_items
            }
        except Exception as e:
            logger.error(f"Error resetting verification message: {e}")
            raise
    
    async def send_verification_message(bot, payload: dict) -> dict:
        """Send verification message to a channel"""
        try:
            channel_id = payload.get('channel_id')
            
            if not channel_id:
                raise ValueError("channel_id is required")
            
            # Get channel
            channel = bot.get_channel(int(channel_id))
            if not channel:
                raise ValueError(f"Channel {channel_id} not found")
            
            # Get message configuration
            cloud_config = db.obter("database/cloud/data.json") or {}
            message_config = cloud_config.get("message_verify", {})
            
            if not message_config:
                raise ValueError("Verification message not configured")
            
            style = message_config.get("message_style", "embed")
            button_data = message_config.get("button", {})
            
            if not button_data.get("label"):
                raise ValueError("Button not configured")
            
            # Import necessary modules
            from functions.utils import utils
            from modules.cloud.container_utils import ContainerUtils
            
            # Prepare send kwargs
            send_kwargs = {}
            
            if style == "embed":
                embed_data = message_config.get("embed", {})
                if not embed_data.get("title"):
                    raise ValueError("Embed content not configured")
                
                normalized_data = utils.normalize_embed_data(embed_data)
                embed = disnake.Embed.from_dict(normalized_data)
                send_kwargs["embed"] = embed
                
            elif style == "content":
                content_data = message_config.get("content", {})
                if not content_data.get("content") and not content_data.get("image_url"):
                    raise ValueError("Content not configured")
                
                send_kwargs["content"] = content_data.get("content")
                # Only send image if URL exists and is not empty
                image_url = content_data.get("image_url")
                if image_url and image_url.strip():
                    send_kwargs["file"] = await utils.url_to_file(image_url, "image.png")
                    
            elif style == "container":
                container_data = message_config.get("container", {})
                if not container_data.get("content"):
                    raise ValueError("Container content not configured")
                
                container = ContainerUtils.montar_container(
                    conteudo=container_data.get("content"),
                    imagem_url=container_data.get("image_url"),
                    cor_hex=container_data.get("color"),
                    thumbnail_url=container_data.get("thumbnail_url")
                )
                
                style_map = {
                    "green": disnake.ButtonStyle.green,
                    "grey": disnake.ButtonStyle.grey,
                    "red": disnake.ButtonStyle.red,
                    "blue": disnake.ButtonStyle.primary
                }
                
                button = disnake.ui.Button(
                    label=button_data.get("label", "Verificar"),
                    style=style_map.get(button_data.get("style", "green")),
                    emoji=button_data.get("emoji") or None,
                    custom_id="Cloud_GetAuthLink"
                )
                
                action_row = disnake.ui.ActionRow(button)
                send_kwargs["components"] = [container, action_row]
                send_kwargs["flags"] = disnake.MessageFlags(is_components_v2=True)
                
                # Send and return early for container
                await channel.send(**send_kwargs)
                return {
                    'success': True,
                    'message': 'Verification message sent successfully',
                    'channel_id': channel_id,
                    'style': style
                }
            
            # Add button for embed and content styles
            style_map = {
                "green": disnake.ButtonStyle.green,
                "grey": disnake.ButtonStyle.grey,
                "red": disnake.ButtonStyle.red,
                "blue": disnake.ButtonStyle.primary
            }
            
            button = disnake.ui.Button(
                label=button_data.get("label", "Verificar"),
                style=style_map.get(button_data.get("style", "green")),
                emoji=button_data.get("emoji") or None,
                custom_id="Cloud_GetAuthLink"
            )
            
            view = disnake.ui.View(timeout=None)
            view.add_item(button)
            send_kwargs["view"] = view
            
            # Send message
            await channel.send(**send_kwargs)
            
            return {
                'success': True,
                'message': 'Verification message sent successfully',
                'channel_id': channel_id,
                'style': style
            }
        except Exception as e:
            logger.error(f"Error sending verification message: {e}")
            raise
    
    # ============= WEBSOCKET CONTROL =============
    
    async def connect_websocket(bot, payload: dict) -> dict:
        """Connect to Sync Cloud WebSocket"""
        try:
            from modules.cloud.update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            if ws_manager.is_connected():
                return {
                    'success': True,
                    'message': 'Already connected',
                    'status': 'connected'
                }
            
            # Start WebSocket
            await ws_manager.start()
            
            return {
                'success': True,
                'message': 'WebSocket connected successfully',
                'status': 'connected'
            }
        except Exception as e:
            logger.error(f"Error connecting WebSocket: {e}")
            raise
    
    async def disconnect_websocket(bot, payload: dict) -> dict:
        """Disconnect from Sync Cloud WebSocket"""
        try:
            from modules.cloud.update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            if not ws_manager.is_connected():
                return {
                    'success': True,
                    'message': 'Already disconnected',
                    'status': 'disconnected'
                }
            
            # Stop WebSocket
            await ws_manager.stop()
            
            return {
                'success': True,
                'message': 'WebSocket disconnected successfully',
                'status': 'disconnected'
            }
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
            raise
    
    async def get_websocket_status(bot, payload: dict) -> dict:
        """Get WebSocket connection status"""
        try:
            from modules.cloud.update_api import get_websocket_manager
            ws_manager = get_websocket_manager()
            
            connection_info = ws_manager.get_connection_info()
            
            return {
                'connected': connection_info.get('connected', False),
                'connecting': connection_info.get('connecting', False),
                'server_url': connection_info.get('server_url'),
                'status': 'connected' if connection_info.get('connected') else 'disconnected'
            }
        except Exception as e:
            logger.error(f"Error getting WebSocket status: {e}")
            raise
    
    # Return all handlers
    return {
        # Configuration
        'cloud.getConfig': get_config,
        'cloud.updateCredentials': update_credentials,
        'cloud.updateLogChannel': update_log_channel,
        'cloud.updateVerifiedRole': update_verified_role,
        
        # Statistics
        'cloud.getStats': get_stats,
        'cloud.getAuthLogs': get_auth_logs,
        
        # Gifts (via Sync Cloud API)
        'cloud.getGifts': get_gifts,
        'cloud.getGift': get_gift,
        'cloud.createGift': create_gift,
        'cloud.updateGift': update_gift,
        'cloud.deleteGift': delete_gift,
        
        # Tasks (local task_manager)
        'cloud.getTasks': get_tasks,
        'cloud.getTask': get_task,
        'cloud.createTask': create_task,
        'cloud.updateTask': update_task,
        'cloud.deleteTask': delete_task,
        
        # Verification Message
        'cloud.getVerificationMessage': get_verification_message,
        'cloud.updateVerificationMessage': update_verification_message,
        'cloud.updateMessageStyle': update_message_style,
        'cloud.resetVerificationMessage': reset_verification_message,
        'cloud.sendVerificationMessage': send_verification_message,
        
        # WebSocket Control
        'cloud.connectWebSocket': connect_websocket,
        'cloud.disconnectWebSocket': disconnect_websocket,
        'cloud.getWebSocketStatus': get_websocket_status,
    }
