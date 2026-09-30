"""
Gerenciador de planos do bot.
Controla quais funcionalidades estão disponíveis baseado no plano configurado.
"""

import json
import os

CONFIG_PATH = "configs/config_plan.json"

def get_plan() -> str:
    """
    Obtém o plano atual configurado.
    
    Returns:
        str: O plano atual ("pro", "basic" ou "cloud")
    """
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("plan", "pro").lower()
    except Exception as e:
        print(f"Erro ao ler configs/config_plan.json: {e}")
    
    return "pro"  # Default para pro se houver erro

def is_pro() -> bool:
    """Verifica se o plano é Pro (todas funcionalidades)"""
    return get_plan() == "pro"

def is_basic() -> bool:
    """Verifica se o plano é Basic (sem backup e cloud)"""
    return get_plan() == "basic"

def is_cloud() -> bool:
    """Verifica se o plano é Cloud (apenas painel, anunciar e backup)"""
    return get_plan() == "cloud"

def is_free() -> bool:
    """Verifica se o plano é Free (apenas Sync Wallet como método de pagamento)"""
    return get_plan() == "free"

def should_allow_payment_provider(provider_key: str) -> bool:
    """
    Verifica se um provedor de pagamento pode ser configurado no plano atual.
    
    Args:
        provider_key: Chave do provedor (ex: "sync_wallet", "mercado_pago", etc)
    
    Returns:
        bool: True se o provedor é permitido no plano atual
    """
    plan = get_plan()
    
    if plan == "free":
        # No plano free, apenas Sync Wallet é permitido
        return provider_key == "sync_wallet"
    
    # Outros planos permitem todos os provedores
    return True

def should_load_backup() -> bool:
    """Verifica se o módulo de backup deve ser carregado"""
    plan = get_plan()
    return plan in ["pro", "cloud"]

def should_load_cloud() -> bool:
    """Verifica se o módulo cloud deve ser carregado"""
    plan = get_plan()
    return plan in ["pro", "cloud"]

def should_load_module(module_name: str) -> bool:
    """
    Verifica se um módulo específico deve ser carregado baseado no plano.
    
    Args:
        module_name: Nome do módulo (ex: "automations", "tickets", "settings", "customization", etc)
    
    Returns:
        bool: True se o módulo deve ser carregado
    """
    plan = get_plan()
    
    if plan == "pro":
        return True
    
    if plan == "cloud":
        # No plano cloud, apenas backup, cloud, settings e customization são permitidos
        return module_name in ["backup", "cloud", "settings", "customization"]
    
    if plan == "basic":
        # No plano basic, todos exceto backup e cloud
        return module_name not in ["backup", "cloud"]
    
    if plan == "free":
        # No plano free, todos exceto cloud, protection e backup
        return module_name not in ["cloud", "protection", "backup"]
    
    return True

def should_load_command(command_name: str) -> bool:
    """
    Verifica se um comando específico deve ser carregado baseado no plano.
    
    Args:
        command_name: Nome do comando (ex: "painel", "backup", "anunciar")
    
    Returns:
        bool: True se o comando deve ser carregado
    """
    plan = get_plan()
    
    if plan == "pro":
        return True
    
    if plan == "cloud":
        # No plano cloud, apenas painel, anunciar e backup
        return command_name in ["painel", "anunciar", "backup"]
    
    if plan == "basic":
        # No plano basic, todos exceto backup
        return command_name != "backup"
    
    if plan == "free":
        # No plano free, remover backup e comandos relacionados a cloud/protection se houver
        return command_name not in ["backup", "cloud", "protection"]
    
    return True

def should_enable_cloud_button() -> bool:
    """Verifica se o botão AmyCloud deve estar habilitado no painel"""
    plan = get_plan()
    return plan in ["pro", "cloud"]

def should_enable_panel_button(button_name: str) -> bool:
    """
    Verifica se um botão específico do painel deve estar habilitado.
    
    Args:
        button_name: Nome do botão do painel (ex: "ticket", "cloud", "personalizacao", etc)
    
    Returns:
        bool: True se o botão deve estar habilitado
    """
    # Mapeamento: nome do botão -> nome do módulo
    button_to_module = {
        "loja": "loja",
        "ticket": "tickets",
        "cloud": "cloud",
        "personalizacao": "customization",
        "automacoes": "automations",
        "protection": "protection",
        "sorteios": "giveaways",
        "configuracoes": "settings",
        "rendimentos": "rendimentos"
    }
    
    plan = get_plan()
    
    if plan == "pro":
        return True
    
    if plan == "cloud":
        # No plano cloud, apenas AmyCloud, Configurações e Personalização
        # Verifica pelo nome do módulo
        module_name = button_to_module.get(button_name, button_name)
        return module_name in ["cloud", "settings", "customization"]
    
    if plan == "basic":
        # No plano basic, todos exceto cloud
        module_name = button_to_module.get(button_name, button_name)
        return module_name != "cloud"
    
    if plan == "free":
        # No plano free, remover cloud, protection e backup
        module_name = button_to_module.get(button_name, button_name)
        return module_name not in ["cloud", "protection", "backup"]

    return True

def should_enable_settings_button(button_name: str) -> bool:
    """
    Verifica se um botão específico de configurações deve estar habilitado.
    
    Args:
        button_name: Nome do botão (ex: "cargos", "canais", "pagamentos", etc)
    
    Returns:
        bool: True se o botão deve estar habilitado
    """
    plan = get_plan()
    
    if plan == "pro":
        return True
    
    if plan == "cloud":
        # No plano cloud, apenas Cargos e Canais
        return button_name in ["cargos", "canais"]
    
    if plan == "basic":
        return True
    
    return True
