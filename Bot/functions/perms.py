from functions.database import database as db
import time
import threading


class perms:
    """
    Sistema de permissões do bot com cache de 5 segundos.
    O owner do bot (definido no config.json) sempre tem permissão automática.
    """
    # Cache específico para permissões com TTL de 5 segundos
    _perms_cache: list = None
    _owner_id: str = None
    _cache_time: float = 0
    _cache_lock = threading.Lock()
    _cache_ttl = 5  # 5 segundos

    @staticmethod
    def _load_config_owner():
        """Carrega o owner do config.json local (só precisa ser chamado uma vez)"""
        if perms._owner_id is None:
            config = db.obter("config.json")
            perms._owner_id = config.get("bot", {}).get("owner", "")
        return perms._owner_id
    
    @staticmethod
    def _refresh_cache():
        """Atualiza o cache de permissões do MongoDB se expirado"""
        with perms._cache_lock:
            current_time = time.time()
            if perms._perms_cache is None or (current_time - perms._cache_time) >= perms._cache_ttl:
                perms_doc = db.get_document("bot_permissions")
                perms._perms_cache = perms_doc.get("users", [])
                perms._cache_time = current_time
    
    @staticmethod
    async def check(user_id) -> bool:
        """
        Verifica se usuário tem permissão de admin do bot.
        O owner sempre tem permissão automática.
        """
        user_id_str = str(user_id)
        owner_id = perms._load_config_owner()
        
        # Owner sempre tem permissão
        if user_id_str == owner_id:
            return True
        
        perms._refresh_cache()
        return user_id_str in perms._perms_cache

    @staticmethod
    async def check_owner(user_id) -> bool:
        """Verifica se usuário é o owner do bot"""
        owner_id = perms._load_config_owner()
        return str(user_id) == owner_id
    
    @staticmethod
    def get_owner_id() -> str:
        """Retorna o ID do owner do bot"""
        return perms._load_config_owner()
    
    @staticmethod
    def get_all_users() -> list:
        """Retorna lista de todos usuários com permissão (exceto owner)"""
        perms._refresh_cache()
        return perms._perms_cache.copy()
    
    @staticmethod
    def add_user(user_id: str):
        """Adiciona usuário às permissões"""
        user_id_str = str(user_id)
        perms._refresh_cache()
        if user_id_str not in perms._perms_cache:
            perms._perms_cache.append(user_id_str)
            db.save_document("bot_permissions", {"users": perms._perms_cache})
            perms._cache_time = time.time()  # Atualizar timestamp do cache
    
    @staticmethod
    def remove_user(user_id: str):
        """Remove usuário das permissões"""
        user_id_str = str(user_id)
        perms._refresh_cache()
        if user_id_str in perms._perms_cache:
            perms._perms_cache.remove(user_id_str)
            db.save_document("bot_permissions", {"users": perms._perms_cache})
            perms._cache_time = time.time()  # Atualizar timestamp do cache
    
    @staticmethod
    def clear_cache():
        """Limpa o cache forçando reload na próxima verificação"""
        with perms._cache_lock:
            perms._perms_cache = None
            perms._cache_time = 0