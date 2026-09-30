import json
import uuid
from datetime import datetime
from functions.database import database as db

def get_tasks_data():
    """Obtém dados das tasks"""
    try:
        tasks = db.get_document("cloud_tasks") or []
        if not isinstance(tasks, list):
            tasks = []
        
        # Contar tasks por status
        running = len([t for t in tasks if t.get("status") == "running"])
        finished = len([t for t in tasks if t.get("status") == "finished"])
        error = len([t for t in tasks if t.get("status") == "error"])
        
        return {
            "running": running,
            "finished": finished,
            "error": error,
            "total": len(tasks)
        }
    except Exception:
        return {
            "running": 0,
            "finished": 0,
            "error": 0,
            "total": 0
        }

def create_task(task_type: str, user_id: str, user_name: str, data: dict = None) -> str:
    """Cria uma nova task"""
    try:
        tasks = db.get_document("cloud_tasks") or []
        if not isinstance(tasks, list):
            tasks = []
        
        # Gerar ID único para a task
        task_id = str(uuid.uuid4())
        
        # Mapear tipos de task para nomes legíveis
        task_names = {
            "recover_members": "Recuperar membros",
            "verify_members": "Verificar membros",
            "send_dms": "Enviar DMs",
            "list_members": "Listagem de membros"
        }
        
        # Criar nova task
        new_task = {
            "id": task_id,
            "type": task_type,
            "name": task_names.get(task_type, "Tarefa desconhecida"),
            "status": "running",
            "created_by": {
                "id": user_id,
                "name": user_name
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "data": (data or {})
        }
        
        # Adicionar task à lista
        tasks.append(new_task)
        
        # Salvar no database
        db.save_document("cloud_tasks", tasks)
        
        return task_id
        
    except Exception as e:
        print(f"Erro ao criar task na database: {e}")
        import traceback
        traceback.print_exc()
        return None

def update_task_status(task_id: str, status: str, data: dict = None):
    """Atualiza o status de uma task"""
    try:
        tasks = db.get_document("cloud_tasks") or []
        if not isinstance(tasks, list):
            return False
        
        # Encontrar a task
        for task in tasks:
            if task.get("id") == task_id:
                task["status"] = status
                task["updated_at"] = datetime.now().isoformat()
                
                if data:
                    task["data"].update(data)
                
                # Salvar no arquivo
                db.save_document("cloud_tasks", tasks)
                return True
        
        return False
        
    except Exception as e:
        print(f"Erro ao atualizar task na database: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_task(task_id: str) -> dict:
    """Obtém uma task específica"""
    try:
        tasks = db.get_document("cloud_tasks") or []
        
        if not isinstance(tasks, list):
            return None
        
        for task in tasks:
            if task.get("id") == task_id:
                return task
        
        return None
        
    except Exception:
        return None

def get_all_tasks() -> list:
    """Obtém todas as tasks"""
    try:
        tasks = db.get_document("cloud_tasks") or []
        if not isinstance(tasks, list):
            return []
        
        # Ordenar por data de criação (mais recentes primeiro)
        return sorted(tasks, key=lambda x: x.get("created_at", ""), reverse=True)
        
    except Exception:
        return []

def delete_task(task_id: str) -> bool:
    """Remove uma task"""
    try:
        tasks = db.get_document("cloud_tasks") or []
        if not isinstance(tasks, list):
            return False
        
        # Remover a task
        tasks = [t for t in tasks if t.get("id") != task_id]
        
        # Salvar no database
        db.save_document("cloud_tasks", tasks)
        return True
        
    except Exception as e:
        print(f"Erro ao deletar task na database: {e}")
        import traceback
        traceback.print_exc()
        return False
