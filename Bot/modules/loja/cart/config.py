"""
Configurações centralizadas do sistema de carrinho
"""
from typing import Dict, Any

# Timeouts
CART_TIMEOUT_MINUTES = 15  # Tempo para expirar carrinho pendente
CART_CLEANUP_DAYS = 3  # Dias para limpar carrinhos aprovados

# Limites
MAX_QUANTITY_PER_PURCHASE = 1000000  # Quantidade máxima por compra
MIN_QUANTITY_PER_PURCHASE = 1  # Quantidade mínima por compra

# Mensagens padrão
MESSAGES = {
    "cart_created": "🛒 **Carrinho Criado**\nSeu carrinho foi criado com sucesso!",
    "cart_expired": "⏰ **Carrinho Expirado**\nSeu carrinho foi fechado automaticamente após {minutes} minutos sem pagamento.",
    "cart_cancelled": "❌ **Compra Cancelada**\nSua compra foi cancelada com sucesso.",
    "cart_approved": "✅ **Pagamento Aprovado**\nSeu pagamento foi aprovado com sucesso!",
    "dm_closed": "⚠️ **DM Fechada**\nNão foi possível enviar os itens por DM. Os itens serão entregues aqui no carrinho.",
    "maintenance": "🔧 **Sistema em Manutenção**\n{message}",
    "no_stock": "📦 **Sem Estoque**\nDesculpe, não há estoque suficiente para este produto.",
    "invalid_quantity": "❌ **Quantidade Inválida**\nPor favor, insira uma quantidade entre {min} e {max}.",
    "invalid_coupon": "❌ **Cupom Inválido**\nO cupom informado não existe ou expirou.",
    "payment_pending": "⏳ **Aguardando Pagamento**\nSeu pagamento está sendo processado...",
    "delivery_success": "📦 **Entrega Realizada**\nSeus itens foram entregues com sucesso!",
    "copy_product": "📋 **Produto Copiado**\nOs dados do produto foram copiados para a área de transferência."
}

# Status de carrinho
CART_STATUS = {
    "PENDING": "pending",
    "APPROVED": "approved",
    "CANCELLED": "cancelled",
    "EXPIRED": "expired",
    "DELIVERED": "delivered"
}

# Cores padrão
COLORS = {
    "success": 0x43B581,  # Verde
    "warning": 0xFAA61A,  # Amarelo
    "error": 0xF04747,    # Vermelho
    "info": 0x7289DA,     # Azul
    "default": 0x2F3136   # Cinza escuro
}

def get_maintenance_config() -> Dict[str, Any]:
    """Obtém configuração de manutenção do database"""
    from functions.database import database as db
    
    config = db.get_document("loja_maintenance") or {}
    return {
        "enabled": config.get("enabled", False),
        "message": config.get("message", MESSAGES["maintenance"]),
        "allow_admins": config.get("allow_admins", True)
    }

def is_maintenance_active(user_id: int = None) -> tuple[bool, str]:
    """
    Verifica se o sistema está em manutenção
    Retorna (is_active, message)
    """
    from functions.database import database as db
    
    config = get_maintenance_config()
    
    if not config["enabled"]:
        return False, ""
    
    # Verificar se é admin e se admins podem comprar durante manutenção
    if user_id and config["allow_admins"]:
        cargos = db.get_document("cargos") or {}
        admin_role_id = cargos.get("cargo_admin")
        
        if admin_role_id:
            # Aqui você verificaria se o usuário tem o cargo de admin
            # Por enquanto, retornamos True para manutenção ativa
            pass
    
    return True, config["message"]
