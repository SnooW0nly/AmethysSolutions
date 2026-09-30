"""
Gerenciador centralizado de saldo
Fornece métodos para obter, adicionar, usar e reembolsar saldo dos usuários
"""
from datetime import datetime
from typing import Optional, Dict, List
from functions.database import database as db


class BalanceManager:
    """Gerenciador de saldo de usuários"""
    
    @staticmethod
    def _get_config() -> dict:
        """Obtém configuração do sistema de saldo"""
        return db.get_document("loja_saldo_config") or {}
    
    @staticmethod
    def _get_users_doc() -> dict:
        """Obtém documento de usuários"""
        return db.get_document("loja_saldo_users") or {"users": {}}
    
    @staticmethod
    def _save_users_doc(doc: dict) -> None:
        """Salva documento de usuários"""
        db.save_document("loja_saldo_users", doc)
    
    @staticmethod
    def is_enabled() -> bool:
        """Verifica se o sistema de saldo está ativo"""
        config = BalanceManager._get_config()
        return config.get("enabled", False)
    
    @staticmethod
    def get_user_data(user_id: int) -> dict:
        """Obtém dados de saldo de um usuário"""
        doc = BalanceManager._get_users_doc()
        users = doc.get("users", {})
        return users.get(str(user_id), {
            "balance": 0,
            "total_deposited": 0,
            "total_used": 0,
            "deposits": [],
            "transactions": []
        })
    
    @staticmethod
    def get_user_balance(user_id: int) -> float:
        """Obtém o saldo atual do usuário"""
        user_data = BalanceManager.get_user_data(user_id)
        return user_data.get("balance", 0)
    
    @staticmethod
    def add_balance(
        user_id: int,
        amount: float,
        bonus: float = 0,
        deposit_id: Optional[str] = None,
        payment_method: str = "pix"
    ) -> dict:
        """
        Adiciona saldo ao usuário
        
        Args:
            user_id: ID do usuário
            amount: Valor depositado
            bonus: Valor de bônus
            deposit_id: ID do depósito
            payment_method: Método de pagamento
            
        Returns:
            dict: Dados atualizados do usuário
        """
        doc = BalanceManager._get_users_doc()
        users = doc.get("users", {})
        
        user_data = users.get(str(user_id), {
            "balance": 0,
            "total_deposited": 0,
            "total_used": 0,
            "deposits": [],
            "transactions": []
        })
        
        total_credit = amount + bonus
        
        # Atualizar saldo
        user_data["balance"] = user_data.get("balance", 0) + total_credit
        user_data["total_deposited"] = user_data.get("total_deposited", 0) + amount
        
        # Registrar depósito
        deposit_record = {
            "id": deposit_id or str(int(datetime.utcnow().timestamp())),
            "amount": amount,
            "bonus": bonus,
            "total_credit": total_credit,
            "payment_method": payment_method,
            "timestamp": int(datetime.utcnow().timestamp())
        }
        user_data.setdefault("deposits", []).append(deposit_record)
        
        # Registrar transação
        transaction = {
            "type": "deposit",
            "amount": total_credit,
            "deposit_amount": amount,
            "bonus": bonus,
            "reference_id": deposit_id,
            "description": f"Depósito via {payment_method.upper()}",
            "timestamp": int(datetime.utcnow().timestamp())
        }
        user_data.setdefault("transactions", []).append(transaction)
        
        users[str(user_id)] = user_data
        doc["users"] = users
        BalanceManager._save_users_doc(doc)
        
        return user_data
    
    @staticmethod
    def use_balance(
        user_id: int,
        amount: float,
        reference_id: Optional[str] = None,
        description: str = "Uso de saldo"
    ) -> tuple[bool, str]:
        """
        Usa saldo do usuário
        
        Args:
            user_id: ID do usuário
            amount: Valor a usar
            reference_id: ID de referência (ex: carrinho)
            description: Descrição do uso
            
        Returns:
            tuple: (success, message)
        """
        doc = BalanceManager._get_users_doc()
        users = doc.get("users", {})
        
        user_data = users.get(str(user_id))
        if not user_data:
            return False, "Usuário não possui saldo"
        
        current_balance = user_data.get("balance", 0)
        if current_balance < amount:
            return False, f"Saldo insuficiente. Disponível: R$ {current_balance:.2f}"
        
        # Deduzir saldo
        user_data["balance"] = current_balance - amount
        user_data["total_used"] = user_data.get("total_used", 0) + amount
        
        # Registrar transação
        transaction = {
            "type": "usage",
            "amount": -amount,
            "reference_id": reference_id,
            "description": description,
            "timestamp": int(datetime.utcnow().timestamp())
        }
        user_data.setdefault("transactions", []).append(transaction)
        
        users[str(user_id)] = user_data
        doc["users"] = users
        BalanceManager._save_users_doc(doc)
        
        return True, f"R$ {amount:.2f} deduzido do saldo"
    
    @staticmethod
    def refund_balance(
        user_id: int,
        amount: float,
        reference_id: Optional[str] = None,
        description: str = "Reembolso"
    ) -> tuple[bool, str]:
        """
        Reembolsa saldo ao usuário
        
        Args:
            user_id: ID do usuário
            amount: Valor a reembolsar
            reference_id: ID de referência
            description: Descrição do reembolso
            
        Returns:
            tuple: (success, message)
        """
        doc = BalanceManager._get_users_doc()
        users = doc.get("users", {})
        
        user_data = users.get(str(user_id), {
            "balance": 0,
            "total_deposited": 0,
            "total_used": 0,
            "deposits": [],
            "transactions": []
        })
        
        # Adicionar saldo
        user_data["balance"] = user_data.get("balance", 0) + amount
        user_data["total_used"] = max(0, user_data.get("total_used", 0) - amount)
        
        # Registrar transação
        transaction = {
            "type": "refund",
            "amount": amount,
            "reference_id": reference_id,
            "description": description,
            "timestamp": int(datetime.utcnow().timestamp())
        }
        user_data.setdefault("transactions", []).append(transaction)
        
        users[str(user_id)] = user_data
        doc["users"] = users
        BalanceManager._save_users_doc(doc)
        
        return True, f"R$ {amount:.2f} reembolsado"
    
    @staticmethod
    def get_deposit_history(user_id: int, limit: int = 10) -> List[dict]:
        """Obtém histórico de depósitos do usuário"""
        user_data = BalanceManager.get_user_data(user_id)
        deposits = user_data.get("deposits", [])
        return sorted(deposits, key=lambda x: x.get("timestamp", 0), reverse=True)[:limit]
    
    @staticmethod
    def get_transaction_history(user_id: int, limit: int = 20) -> List[dict]:
        """Obtém histórico de transações do usuário"""
        user_data = BalanceManager.get_user_data(user_id)
        transactions = user_data.get("transactions", [])
        return sorted(transactions, key=lambda x: x.get("timestamp", 0), reverse=True)[:limit]
    
    @staticmethod
    def calculate_bonus(amount: float) -> float:
        """
        Calcula o bônus para um valor de depósito
        
        Args:
            amount: Valor do depósito
            
        Returns:
            float: Valor do bônus
        """
        config = BalanceManager._get_config()
        bonus_config = config.get("bonus", {})
        bonus_type = bonus_config.get("type", "disabled")
        bonus_value = bonus_config.get("value", 0)
        
        if bonus_type == "disabled" or bonus_value <= 0:
            return 0
        
        if bonus_type == "percentage":
            return amount * (bonus_value / 100)
        elif bonus_type == "fixed":
            return bonus_value
        
        return 0
    
    @staticmethod
    def calculate_usable_amount(user_id: int, purchase_amount: float) -> float:
        """
        Calcula quanto do saldo pode ser usado em uma compra
        
        Args:
            user_id: ID do usuário
            purchase_amount: Valor da compra
            
        Returns:
            float: Valor máximo que pode ser usado
        """
        config = BalanceManager._get_config()
        rules = config.get("rules", {})
        
        user_balance = BalanceManager.get_user_balance(user_id)
        
        if user_balance <= 0:
            return 0
        
        # Valor mínimo de uso
        min_usage = rules.get("min_usage_amount", 0) or 0
        if purchase_amount < min_usage:
            return 0
        
        # Valor máximo pelo saldo
        max_usable = min(user_balance, purchase_amount)
        
        # Limitação por porcentagem
        max_percentage = rules.get("max_usage_percentage", 100) or 100
        max_by_percentage = purchase_amount * (max_percentage / 100)
        max_usable = min(max_usable, max_by_percentage)
        
        # Limitação por valor máximo
        max_amount = rules.get("max_usage_amount")
        if max_amount and max_amount > 0:
            max_usable = min(max_usable, max_amount)
        
        return max(0, max_usable)
