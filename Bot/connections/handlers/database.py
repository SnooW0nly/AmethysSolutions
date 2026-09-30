"""Database handlers for WebSocket"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any
from functions.database import database as db

logger = logging.getLogger(__name__)

def register_database_handlers():
    """Register all database handlers"""
    
    async def backup(bot, payload: dict) -> dict:
        """Create database backup"""
        try:
            # Create backup directory if not exists
            backup_dir = 'database/backups'
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = f"{backup_dir}/backup_{timestamp}.json"
            
            # Get all database documents
            backup_data = {}
            collections = [
                'products', 'orders', 'carts', 'tickets', 'giveaways',
                'automations', 'protection_config', 'welcome_config',
                'leave_config', 'general_settings', 'permissions',
                'payment_configs', 'pagamentos', 'loja_config',
                'tickets_config', 'rendimentos_config', 'earnings'
            ]
            
            for collection in collections:
                data = db.get_document(collection)
                if data:
                    backup_data[collection] = data
            
            # Save backup
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Get file size
            file_size = os.path.getsize(backup_file) / 1024  # KB
            
            return {
                'success': True,
                'filename': backup_file,
                'size': f"{file_size:.2f} KB",
                'collections': len(backup_data),
                'timestamp': timestamp
            }
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
    
    async def restore(bot, payload: dict) -> dict:
        """Restore database backup"""
        try:
            backup_id = payload.get('backupId')
            if not backup_id:
                raise ValueError("backupId is required")
            
            backup_file = f"database/backups/backup_{backup_id}.json"
            
            if not os.path.exists(backup_file):
                raise ValueError(f"Backup file {backup_id} not found")
            
            # Load backup data
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Restore each collection
            restored = []
            for collection, data in backup_data.items():
                db.save_document(collection, data)
                restored.append(collection)
            
            return {
                'success': True,
                'message': 'Database restored successfully',
                'restored': restored,
                'count': len(restored)
            }
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            raise
    
    async def export_data(bot, payload: dict) -> dict:
        """Export specific collection data"""
        try:
            collection = payload.get('collection')
            if not collection:
                raise ValueError("collection is required")
            
            data = db.get_document(collection)
            
            if not data:
                return {
                    'success': False,
                    'message': f'Collection {collection} is empty or not found'
                }
            
            # Convert to exportable format
            if isinstance(data, dict):
                export_data = list(data.values()) if all(isinstance(k, str) for k in data.keys()) else data
            else:
                export_data = data
            
            return {
                'success': True,
                'collection': collection,
                'data': export_data,
                'count': len(export_data) if isinstance(export_data, (list, dict)) else 1
            }
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            raise
    
    async def import_data(bot, payload: dict) -> dict:
        """Import data to collection"""
        try:
            collection = payload.get('collection')
            data = payload.get('data')
            
            if not collection or data is None:
                raise ValueError("collection and data are required")
            
            # Save to database
            db.save_document(collection, data)
            
            return {
                'success': True,
                'message': f'Data imported to {collection}',
                'count': len(data) if isinstance(data, (list, dict)) else 1
            }
        except Exception as e:
            logger.error(f"Error importing data: {e}")
            raise
    
    return {
        'database.backup': backup,
        'database.restore': restore,
        'database.export': export_data,
        'database.import': import_data
    }
