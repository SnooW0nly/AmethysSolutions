"""
Gerenciador de Cashback
Fornece métodos para calcular e aplicar cashback aos usuários
"""
from typing import Optional, Dict, List
from functions.database import database as db


class CashbackManager:
    """Gerenciador de cashback"""
    
    CONFIG_DOC = "loja_cashback_config"
    
    @staticmethod
    def _get_config() -> dict:
        """Obtém configuração do sistema de cashback"""
        config = db.get_document(CashbackManager.CONFIG_DOC)
        if not config:
            config = {
                "enabled": False,
                "default_percentage": 5.0,
                "max_cashback": None,
                "rules": []
            }
            db.save_document(CashbackManager.CONFIG_DOC, config)
        return config
    
    @staticmethod
    def _save_config(config: dict):
        """Salva configuração"""
        db.save_document(CashbackManager.CONFIG_DOC, config)
    
    @staticmethod
    def is_balance_enabled() -> bool:
        """Verifica se o sistema de saldo está habilitado"""
        saldo_config = db.get_document("loja_saldo_config") or {}
        return saldo_config.get("enabled", False)
    
    @staticmethod
    def is_enabled() -> bool:
        """Verifica se o sistema de cashback está ativo"""
        config = CashbackManager._get_config()
        return config.get("enabled", False) and CashbackManager.is_balance_enabled()
    
    @staticmethod
    def can_enable() -> tuple:
        """Verifica se pode ativar o cashback (requer saldo ativo)"""
        if not CashbackManager.is_balance_enabled():
            return False, "O sistema de saldo precisa estar ativo para usar o cashback."
        return True, None
    
    @staticmethod
    def set_enabled(enabled: bool) -> tuple:
        """Ativa ou desativa o sistema"""
        if enabled:
            can_enable, message = CashbackManager.can_enable()
            if not can_enable:
                return False, message
        
        config = CashbackManager._get_config()
        config["enabled"] = enabled
        CashbackManager._save_config(config)
        return True, None
    
    @staticmethod
    def get_default_percentage() -> float:
        """Obtém porcentagem padrão de cashback"""
        config = CashbackManager._get_config()
        return config.get("default_percentage", 5.0)
    
    @staticmethod
    def set_default_percentage(percentage: float) -> bool:
        """Define porcentagem padrão"""
        if percentage < 0 or percentage > 100:
            return False
        config = CashbackManager._get_config()
        config["default_percentage"] = percentage
        CashbackManager._save_config(config)
        return True
    
    @staticmethod
    def get_rules() -> List[dict]:
        """Obtém lista de regras por cargo"""
        config = CashbackManager._get_config()
        return config.get("rules", [])
    
    @staticmethod
    def add_rule(role_id: int, role_name: str, multiplier: float) -> bool:
        """Adiciona regra de cargo"""
        if multiplier <= 0:
            return False
        
        config = CashbackManager._get_config()
        rules = config.get("rules", [])
        
        # Remove regra existente para o mesmo cargo
        rules = [r for r in rules if str(r.get("role_id")) != str(role_id)]
        
        rules.append({
            "role_id": str(role_id),
            "role_name": role_name,
            "multiplier": multiplier
        })
        
        config["rules"] = rules
        CashbackManager._save_config(config)
        return True
    
    @staticmethod
    def remove_rule(role_id: int) -> bool:
        """Remove regra de cargo"""
        config = CashbackManager._get_config()
        rules = config.get("rules", [])
        
        original_len = len(rules)
        rules = [r for r in rules if str(r.get("role_id")) != str(role_id)]
        
        if len(rules) == original_len:
            return False
        
        config["rules"] = rules
        CashbackManager._save_config(config)
        return True
    
    @staticmethod
    def get_multiplier_for_user(user_roles: List[int]) -> float:
        """Obtém o maior multiplicador aplicável ao usuário"""
        rules = CashbackManager.get_rules()
        max_multiplier = 1.0
        
        user_role_strs = [str(r) for r in user_roles]
        
        for rule in rules:
            if str(rule.get("role_id")) in user_role_strs:
                multiplier = rule.get("multiplier", 1.0)
                if multiplier > max_multiplier:
                    max_multiplier = multiplier
        
        return max_multiplier
    
    @staticmethod
    def calculate_cashback(amount: float, user_roles: List[int]) -> float:
        """
        Calcula o valor de cashback para uma compra
        
        Args:
            amount: Valor da compra
            user_roles: IDs dos cargos do usuário
            
        Returns:
            float: Valor do cashback
        """
        if not CashbackManager.is_enabled():
            return 0.0
        
        config = CashbackManager._get_config()
        base_percentage = config.get("default_percentage", 5.0)
        max_cashback = config.get("max_cashback")
        
        # Aplicar multiplicador por cargo
        multiplier = CashbackManager.get_multiplier_for_user(user_roles)
        final_percentage = base_percentage * multiplier
        
        # Calcular cashback
        cashback = (amount * final_percentage) / 100
        
        # Aplicar limite máximo se definido
        if max_cashback and cashback > max_cashback:
            cashback = max_cashback
        
        return round(cashback, 2)
    
    @staticmethod
    def apply_cashback(user_id: int, amount: float, purchase_ref: str = None) -> tuple:
        """
        Aplica cashback ao saldo do usuário
        
        Args:
            user_id: ID do usuário
            amount: Valor do cashback
            purchase_ref: Referência da compra
            
        Returns:
            tuple: (success, message)
        """
        if amount <= 0:
            return False, "Valor de cashback inválido"
        
        if not CashbackManager.is_enabled():
            return False, "Sistema de cashback desativado"
        
        try:
            from ..saldo.balance_manager import BalanceManager
            BalanceManager.add_balance(
                user_id,
                amount,
                bonus=0,
                deposit_id=f"cashback_{purchase_ref}" if purchase_ref else "cashback",
                payment_method="cashback"
            )
            return True, f"Cashback de R$ {amount:.2f} aplicado!"
        except Exception as e:
            return False, str(e)
