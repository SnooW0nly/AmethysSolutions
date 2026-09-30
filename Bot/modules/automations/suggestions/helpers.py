from functions.database import database as db
import uuid
from datetime import datetime

def truncar_texto(texto: str, limite: int, sufixo: str = "...") -> str:
    """Trunca um texto respeitando um limite de caracteres, tentando não cortar palavras."""
    if not texto or len(texto) <= limite:
        return texto
    
    # Se o limite é muito pequeno, apenas trunca
    if limite <= len(sufixo):
        return texto[:limite]
    
    texto_truncado = texto[:limite - len(sufixo)]
    
    # Tenta encontrar o último espaço para não cortar palavras
    ultimo_espaco = texto_truncado.rfind(' ')
    if ultimo_espaco > limite * 0.7:  # Se encontrou um espaço em uma posição razoável
        texto_truncado = texto_truncado[:ultimo_espaco]
    
    return texto_truncado + sufixo

def truncar_para_embed_description(texto: str) -> str:
    """Trunca texto para uso em embed description (limite seguro: 2000 caracteres)."""
    return truncar_texto(texto, 2000)

def truncar_para_embed_field(texto: str) -> str:
    """Trunca texto para uso em embed field value (limite: 1024 caracteres)."""
    return truncar_texto(texto, 1024)

def truncar_para_mensagem(texto: str) -> str:
    """Trunca texto para uso em mensagem normal (limite: 2000 caracteres)."""
    return truncar_texto(texto, 2000)

class SuggestionsDB:
    def __init__(self):
        # O nome da coleção agora define o "arquivo" no MongoDB.
        self.collection_name = "automations_suggestions"

    def get_config(self):
        """Obtém a configuração principal do documento no MongoDB."""
        return db.get_document(self.collection_name)

    def _save_config(self, data):
        """Salva todo o documento de configuração."""
        db.save_document(self.collection_name, {}, data)

    def set_status(self, status: bool):
        config = self.get_config()
        config['status'] = status
        self._save_config(config)

    def set_channel(self, channel_id: int | None):
        config = self.get_config()
        config['channel'] = channel_id
        self._save_config(config)

    def set_immune_role(self, role_id: int | None):
        config = self.get_config()
        config['immune_role_id'] = role_id
        self._save_config(config)

    def set_create_threads(self, status: bool):
        config = self.get_config()
        config['create_threads'] = status
        self._save_config(config)

    def set_thread_message(self, message: str):
        config = self.get_config()
        config['thread_message'] = message
        self._save_config(config)

    def set_auto_moderation(self, new_auto_mod_config: dict):
        config = self.get_config()
        config['auto_moderation'] = new_auto_mod_config
        self._save_config(config)

    def add_suggestion(self, author_id: int, content: str, message_type: str) -> str:
        config = self.get_config()
        sugestao_id = str(uuid.uuid4())
        
        if "sugestoes" not in config:
            config["sugestoes"] = {}
            
        config["sugestoes"][sugestao_id] = {
            "author_id": author_id,
            "content": content,
            "upvotes": [],

            "downvotes": [],
            "status": "aberta",
            "message_type": message_type,
            "created_at": datetime.utcnow().isoformat()
        }
        self._save_config(config)
        return sugestao_id

    def update_suggestion_message_id(self, sugestao_id: str, message_id: int):
        config = self.get_config()
        if sugestao_id in config.get("sugestoes", {}):
            config["sugestoes"][sugestao_id]["message_id"] = message_id
            self._save_config(config)
    
    def update_vote(self, sugestao_id: str, user_id: int, is_upvote: bool):
        config = self.get_config()
        sugestao = config.get("sugestoes", {}).get(sugestao_id)
        if not sugestao:
            return

        upvotes = sugestao.get("upvotes", [])
        downvotes = sugestao.get("downvotes", [])

        if is_upvote:
            if user_id in upvotes:
                upvotes.remove(user_id)
            else:
                upvotes.append(user_id)
                if user_id in downvotes:
                    downvotes.remove(user_id)
        else:
            if user_id in downvotes:
                downvotes.remove(user_id)
            else:
                downvotes.append(user_id)
                if user_id in upvotes:
                    upvotes.remove(user_id)
        
        sugestao["upvotes"] = upvotes
        sugestao["downvotes"] = downvotes
        self._save_config(config)

    def update_status(self, sugestao_id: str, status: str, moderator_id: int):
        config = self.get_config()
        sugestao = config.get("sugestoes", {}).get(sugestao_id)
        if not sugestao:
            return
        sugestao["status"] = status
        sugestao["moderator_id"] = moderator_id
        self._save_config(config)

    def delete_suggestion(self, sugestao_id: str):
        config = self.get_config()
        if sugestao_id in config.get("sugestoes", {}):
            del config["sugestoes"][sugestao_id]
            self._save_config(config)
