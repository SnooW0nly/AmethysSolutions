import os
import json
import datetime

BACKUP_DIR = 'database/backups'

class Backup:
    @staticmethod
    def ListarBackups():
        backups = []
        if not os.path.exists(BACKUP_DIR):
            return backups

        for filename in os.listdir(BACKUP_DIR):
            if filename.endswith('.json') and filename != 'restore.json':
                filepath = os.path.join(BACKUP_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    timestamp = None
                    try:
                        parts = filename.replace('.json', '').split('_')
                        date_str = f"{parts[-2]}_{parts[-1]}"
                        dt_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d_%H-%M-%S')
                        timestamp = int(dt_obj.timestamp())
                    except (IndexError, ValueError):
                        timestamp = int(os.path.getmtime(filepath))

                    total_msgs = sum(len(msgs) for msgs in data.get('messages', {}).values())

                    backup_info = {
                        'arquivo': filename,
                        'timestamp': timestamp,
                        'guild': data.get('guild', {}).get('nome', 'Desconhecido'),
                        'canais': len(data.get('channels', [])),
                        'categorias': len(data.get('categories', [])),
                        'cargos': len(data.get('roles', [])),
                        'emojis': len(data.get('emojis', [])),
                        'stickers': len(data.get('stickers', [])),
                        'membros': len(data.get('members', [])),
                        'mensagens': total_msgs,
                    }
                    backups.append(backup_info)
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[Backup] Erro ao ler o arquivo de backup {filename}: {e}")
        
        backups.sort(key=lambda b: b['timestamp'], reverse=True)
        return backups