import asyncio
import time
from functions.database import database as db
from .update_api import get_websocket_manager

# Cache global simples: (count, timestamp)
_auth_count_cache = {"count": 0, "expires": 0}

async def get_auth_count() -> int:
    """Obtém o número de membros autenticados"""
    try:
        # Verificar cache (válido por 30 segundos)
        now = time.time()
        if _auth_count_cache["expires"] > now:
            return _auth_count_cache["count"]

        print("🔍 Iniciando verificação de contagem de membros autenticados...")
        
        # Obter configuração do cloud
        cloud_config = db.get_document("cloud_data") or {}
        bot_id = cloud_config.get("client_id")
        
        print(f"📋 Bot ID configurado: {bot_id}")
        
        if not bot_id:
            print("❌ Bot ID não configurado")
            return 0
        
        # Obter WebSocket manager (funciona via WS ou HTTP fallback)
        ws_manager = get_websocket_manager()
        
        print(f"🔌 Modo conexão: {'WS' if ws_manager.is_connected() else 'HTTP fallback'}")
        
        # Fazer requisição para verificar contagem
        print("📤 Enviando requisição check_auth_count...")
        response = await ws_manager.check_auth_count(bot_id)
        
        print(f"📥 Resposta recebida: {response}")
        
        if response.get("success"):
            auth_count = response.get("data", {}).get("count", 0)
            # Atualizar cache
            _auth_count_cache["count"] = auth_count
            _auth_count_cache["expires"] = time.time() + 30
            print(f"✅ Contagem obtida: {auth_count} membros autenticados")
            return auth_count
        else:
            # Em caso de erro, retornar cache antigo se existir ou 0
            print(f"❌ Erro ao obter contagem: {response.get('message', 'Erro desconhecido')}")
            return _auth_count_cache["count"]
            
    except Exception as e:
        print(f"❌ Erro ao obter contagem de membros autenticados: {e}")
        import traceback
        traceback.print_exc()
        return 0
