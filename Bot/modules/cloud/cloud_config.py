"""
Módulo de configuração centralizada para URLs do Cloud.
Carrega as configurações do config_api.json.
"""
import json
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Cache para evitar leituras repetidas do arquivo
_config_cache: Optional[dict] = None
_config_path: Optional[str] = None


def _get_config_path() -> str:
    """Retorna o caminho do arquivo de configuração."""
    global _config_path
    if _config_path:
        return _config_path
    
    # Tentar diferentes caminhos possíveis
    possible_paths = [
        'configs/config_api.json',
        'vision/configs/config_api.json',
        '../configs/config_api.json',
        os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'config_api.json'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            _config_path = path
            return path
    
    # Fallback para caminho padrão
    _config_path = 'configs/config_api.json'
    return _config_path


def _load_config() -> dict:
    """Carrega a configuração do arquivo config_api.json."""
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    try:
        config_path = _get_config_path()
        with open(config_path, 'r', encoding='utf-8') as f:
            _config_cache = json.load(f)
            return _config_cache
    except FileNotFoundError:
        logger.warning(f"Arquivo config_api.json não encontrado")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao parsear config_api.json: {e}")
        return {}
    except Exception as e:
        logger.error(f"Erro ao carregar config_api.json: {e}")
        return {}


def reload_config() -> dict:
    """Força recarga da configuração do arquivo."""
    global _config_cache
    _config_cache = None
    return _load_config()


def get_cloud_url() -> str:
    """
    Retorna a URL base do Cloud (sem barra no final).
    Exemplo: 'http://localhost:8080' ou 'https://cloud.amethys.solutions'
    """
    config = _load_config()
    cloud_url = config.get('cloud', 'https://cloud.amethys.solutions')
    
    # Remover barra final se existir
    return cloud_url.rstrip('/')


def get_auth_callback_url() -> str:
    """
    Retorna a URL de callback para autenticação OAuth2.
    Exemplo: 'http://localhost:8080/api/auth/callback'
    """
    return f"{get_cloud_url()}/api/auth/callback"


def get_gifts_url(gift_id: str) -> str:
    """
    Retorna a URL para um gift específico.
    Exemplo: 'http://localhost:8080/gifts/{gift_id}'
    """
    return f"{get_cloud_url()}/gifts/{gift_id}"


def get_websocket_url() -> str:
    """
    Retorna a URL do WebSocket baseada na URL do Cloud.
    Converte http/https para ws/wss.
    """
    cloud_url = get_cloud_url()
    
    if cloud_url.startswith('https://'):
        return 'wss://' + cloud_url[8:]
    elif cloud_url.startswith('http://'):
        return 'ws://' + cloud_url[7:]
    else:
        # Se já for ws/wss, retornar como está
        return cloud_url


def get_api_url() -> str:
    """Retorna a URL da API."""
    config = _load_config()
    return config.get('api', 'localhost:22222')


def get_transcripts_url() -> str:
    """Retorna a URL dos transcripts."""
    config = _load_config()
    return config.get('transcripts', 'localhost:22222')
