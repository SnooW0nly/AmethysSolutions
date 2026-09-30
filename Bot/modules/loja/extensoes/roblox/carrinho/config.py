from typing import Dict, Any

from functions.emoji import emoji

ROBUX_TAXA_ROBLOX = 0.30
CART_TIMEOUT_MINUTES = 30

# Métodos de entrega disponíveis
DELIVERY_METHODS = {
    "gamepass": "gamepass",   # Comprador cria gamepass, loja compra
    "group": "group",         # Comprador entra no grupo, loja paga via Group Funds
}

ROBUX_ORDER_STATUS = {
    "PENDING_PAYMENT": "pending_payment",
    "PAYMENT_APPROVED": "payment_approved",
    "PENDING_DELIVERY": "pending_delivery",
    "DELIVERED": "delivered",
    "CANCELLED": "cancelled",
}

MESSAGES = {
    "system_disabled": f"{emoji.wrong} O sistema de venda de Robux está desativado no momento.",
    "robux_disabled": f"{emoji.wrong} A venda de Robux está desativada no momento.",
    "gamepass_disabled": f"{emoji.wrong} A venda de Gamepass está desativada no momento.",
    "invalid_quantity": f"{emoji.wrong} Quantidade inválida. Insira um número entre {min} e {max}.",
    "user_not_found": f"{emoji.wrong} Usuário do Roblox não encontrado.",
    "payment_error": f"{emoji.wrong} Ocorreu um erro ao criar o pagamento. Tente novamente.",
    "ticket_created": f"{emoji.correct} Carrinho criado com sucesso!",
    "ticket_cancelled": f"{emoji.wrong} Compra cancelada.",
    "delivery_done": f"{emoji.correct} Entrega concluída! O carrinho foi encerrado.",
}


def calcular_preco_robux(robux_amount: int, preco_por_mil: float) -> float:
    return round((robux_amount / 1000) * preco_por_mil, 2)


def calcular_robux_bruto(robux_solicitados: int) -> int:
    """Calcula os robux brutos necessários cobrindo a taxa do Roblox (30%)."""
    return int(robux_solicitados / (1 - ROBUX_TAXA_ROBLOX))


def calcular_robux_sem_taxa(robux_solicitados: int) -> int:
    """Sem cobertura de taxa — robux bruto == robux solicitado (cliente paga a taxa do Roblox)."""
    return robux_solicitados


def get_roblox_config() -> Dict[str, Any]:
    from functions.database import database as db
    config = db.get_document("roblox_config") or {}
    return {
        "enabled": config.get("enabled", False),
        "robux_sale_enabled": config.get("robux_sale_enabled", True),
        "gamepass_sale_enabled": config.get("gamepass_sale_enabled", True),
        "preco_por_mil": config.get("preco_por_mil", 32.70),
        "min_robux": config.get("min_robux", 100),
        "max_robux": config.get("max_robux", 100000),
        "canais": config.get("canais", {}),
        "btn_robux": config.get("btn_robux", {"label": "Comprar Robux", "emoji": "💎", "style": "blurple"}),
        "btn_gamepass": config.get("btn_gamepass", {"label": "Comprar Gamepass", "emoji": "🎮", "style": "blurple"}),
        "btn_calcular": config.get("btn_calcular", {"label": "Calcular Preço", "emoji": "🧮", "style": "grey"}),
        # Método de entrega: "gamepass" (padrão) ou "group"
        "delivery_method": config.get("delivery_method", "gamepass"),
        # ID numérico do grupo Roblox (para entrega via Group Funds)
        "group_id": config.get("group_id", None),
        # Link público do grupo (exibido ao comprador)
        "group_link": config.get("group_link", ""),
    }