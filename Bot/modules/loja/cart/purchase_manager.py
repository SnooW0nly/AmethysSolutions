"""
Sistema de gerenciamento de histórico de compras
Armazena dados detalhados de cada compra para métricas e estatísticas
"""
import disnake
from functions.database import database as db
from typing import Dict, List, Optional
import random
import string
import asyncio
from functions.email_utils import _send_email_sync


class PurchaseManager:
    """Gerencia o histórico de compras dos clientes"""
    
    @staticmethod
    def _generate_purchase_id(length: int = 12) -> str:
        """Gera um ID único para a compra"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    @staticmethod
    def _load_purchases() -> dict:
        """Carrega o arquivo de compras"""
        data = db.get_document("loja_buys")
        if not data:
            data = {"purchases": {}}
        if "purchases" not in data:
            data["purchases"] = {}
        return data
    
    @staticmethod
    def _save_purchases(data: dict):
        """Salva o arquivo de compras"""
        db.save_document("loja_buys", data)
    
    @staticmethod
    def register_purchase(
        user_id: int,
        product_id: str,
        product_name: str,
        field_id: str,
        field_name: str,
        quantity: int,
        unit_price: float,
        total_price: float,
        discount_amount: float,
        final_price: float,
        payment_method: str,
        coupon_code: Optional[str] = None,
        items_received: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Registra uma nova compra no histórico
        
        Args:
            user_id: ID do usuário que comprou
            product_id: ID do produto
            product_name: Nome do produto
            field_id: ID do campo/variação
            field_name: Nome do campo/variação
            quantity: Quantidade comprada
            unit_price: Preço unitário
            total_price: Preço total sem desconto
            discount_amount: Valor do desconto aplicado
            final_price: Preço final pago
            payment_method: Método de pagamento usado
            coupon_code: Código do cupom usado (se houver)
            items_received: Lista de itens entregues
            metadata: Dados adicionais (opcional)
        
        Returns:
            str: ID da compra registrada
        """
        data = PurchaseManager._load_purchases()
        
        # Gerar ID único para a compra
        purchase_id = PurchaseManager._generate_purchase_id()
        
        # Garantir que o ID é único
        while purchase_id in [p.get("purchase_id") for purchases in data["purchases"].values() for p in purchases]:
            purchase_id = PurchaseManager._generate_purchase_id()
        
        # Timestamp atual
        timestamp = int(disnake.utils.utcnow().timestamp())
        
        # Criar registro da compra
        purchase_record = {
            "purchase_id": purchase_id,
            "timestamp": timestamp,
            "product": {
                "id": product_id,
                "name": product_name
            },
            "field": {
                "id": field_id,
                "name": field_name
            },
            "quantity": quantity,
            "pricing": {
                "unit_price": unit_price,
                "total_price": total_price,
                "discount_amount": discount_amount,
                "final_price": final_price
            },
            "payment": {
                "method": payment_method,
                "coupon_code": coupon_code
            },
            "delivery": {
                "items": items_received or [],
                "items_count": len(items_received) if items_received else 0
            },
            "metadata": metadata or {}
        }
        
        # Adicionar ao histórico do usuário
        user_id_str = str(user_id)
        if user_id_str not in data["purchases"]:
            data["purchases"][user_id_str] = []
        
        data["purchases"][user_id_str].append(purchase_record)
        
        # Salvar
        PurchaseManager._save_purchases(data)
        
        # Enviar notificação por email (em background)
        asyncio.create_task(PurchaseManager._send_purchase_email_notification(purchase_record, user_id))
        
        return purchase_id

    @staticmethod
    async def _send_purchase_email_notification(purchase: dict, user_id: int):
        """Envia uma notificação de venda por email"""
        try:
            product_name = purchase.get("product", {}).get("name")
            quantity = purchase.get("quantity")
            final_price = purchase.get("pricing", {}).get("final_price")
            method = purchase.get("payment", {}).get("method")
            purchase_id = purchase.get("purchase_id")
            
            subject = f"Nova Venda: {product_name} - ID {purchase_id}"
            
            body_text = (
                f"Nova venda realizada no seu bot!\n\n"
                f"Produto: {product_name}\n"
                f"Quantidade: {quantity}\n"
                f"Valor Pago: R$ {final_price:.2f}\n"
                f"Método: {method}\n"
                f"ID da Compra: {purchase_id}\n"
                f"ID do Usuário: {user_id}\n"
            )
            
            body_html = f"""
            <html>
            <body style="font-family: sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <h2 style="color: #5c5ef0; border-bottom: 2px solid #5c5ef0; padding-bottom: 10px;">Nova Venda Realizada!</h2>
                    <p>Uma nova venda foi processada com sucesso no seu bot.</p>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Produto:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{product_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Quantidade:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{quantity}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Valor Pago:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">R$ {final_price:.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>Método:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{method}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>ID da Compra:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><code>{purchase_id}</code></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><strong>ID do Usuário:</strong></td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;"><code>{user_id}</code></td>
                        </tr>
                    </table>
                    <p style="margin-top: 20px; font-size: 0.9em; color: #777;">
                        Esta é uma notificação automática do seu sistema de vendas.
                    </p>
                </div>
            </body>
            </html>
            """
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _send_email_sync, subject, body_text, body_html)
        except Exception as e:
            print(f"Erro ao processar notificação de email: {e}")
    
    @staticmethod
    def register_generic_payment(
        user_id: int,
        amount: float,
        payment_method: str,
        description: Optional[str] = None,
        payment_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Registra um pagamento genérico (sem produto específico) no histórico
        
        Args:
            user_id: ID do usuário que pagou
            amount: Valor pago
            payment_method: Método de pagamento usado
            description: Descrição do pagamento
            payment_id: ID do pagamento (opcional)
            metadata: Dados adicionais (opcional)
        
        Returns:
            str: ID da compra registrada
        """
        return PurchaseManager.register_purchase(
            user_id=user_id,
            product_id="generic_payment",
            product_name=description or "Pagamento Genérico",
            field_id="none",
            field_name="Pagamento",
            quantity=1,
            unit_price=amount,
            total_price=amount,
            discount_amount=0.0,
            final_price=amount,
            payment_method=payment_method,
            coupon_code=None,
            items_received=[],
            metadata={
                **(metadata or {}),
                "is_generic_payment": True,
                "payment_id": payment_id
            }
        )
    
    @staticmethod
    def get_user_purchases(user_id: int, limit: Optional[int] = None) -> List[Dict]:
        """
        Obtém o histórico de compras de um usuário
        
        Args:
            user_id: ID do usuário
            limit: Limite de compras a retornar (mais recentes primeiro)
        
        Returns:
            List[Dict]: Lista de compras do usuário
        """
        data = PurchaseManager._load_purchases()
        user_id_str = str(user_id)
        
        purchases = data["purchases"].get(user_id_str, [])
        
        # Ordenar por timestamp (mais recente primeiro)
        purchases_sorted = sorted(purchases, key=lambda x: x.get("timestamp", 0), reverse=True)
        
        if limit:
            return purchases_sorted[:limit]
        
        return purchases_sorted
    
    @staticmethod
    def get_purchase_by_id(purchase_id: str) -> Optional[Dict]:
        """
        Busca uma compra específica pelo ID
        
        Args:
            purchase_id: ID da compra
        
        Returns:
            Optional[Dict]: Dados da compra ou None se não encontrada
        """
        data = PurchaseManager._load_purchases()
        
        for user_purchases in data["purchases"].values():
            for purchase in user_purchases:
                if purchase.get("purchase_id") == purchase_id:
                    return purchase
        
        return None
    
    @staticmethod
    def get_all_purchases(limit: Optional[int] = None) -> List[Dict]:
        """
        Obtém todas as compras do sistema
        
        Args:
            limit: Limite de compras a retornar (mais recentes primeiro)
        
        Returns:
            List[Dict]: Lista de todas as compras
        """
        data = PurchaseManager._load_purchases()
        
        all_purchases = []
        for user_id, purchases in data["purchases"].items():
            for purchase in purchases:
                purchase_copy = purchase.copy()
                purchase_copy["user_id"] = user_id
                all_purchases.append(purchase_copy)
        
        # Ordenar por timestamp (mais recente primeiro)
        all_purchases_sorted = sorted(all_purchases, key=lambda x: x.get("timestamp", 0), reverse=True)
        
        if limit:
            return all_purchases_sorted[:limit]
        
        return all_purchases_sorted
    
    @staticmethod
    def get_product_purchases(product_id: str, limit: Optional[int] = None) -> List[Dict]:
        """
        Obtém todas as compras de um produto específico
        
        Args:
            product_id: ID do produto
            limit: Limite de compras a retornar
        
        Returns:
            List[Dict]: Lista de compras do produto
        """
        data = PurchaseManager._load_purchases()
        
        product_purchases = []
        for user_id, purchases in data["purchases"].items():
            for purchase in purchases:
                if purchase.get("product", {}).get("id") == product_id:
                    purchase_copy = purchase.copy()
                    purchase_copy["user_id"] = user_id
                    product_purchases.append(purchase_copy)
        
        # Ordenar por timestamp (mais recente primeiro)
        product_purchases_sorted = sorted(product_purchases, key=lambda x: x.get("timestamp", 0), reverse=True)
        
        if limit:
            return product_purchases_sorted[:limit]
        
        return product_purchases_sorted
    
    @staticmethod
    def get_statistics() -> Dict:
        """
        Calcula estatísticas gerais de vendas
        
        Returns:
            Dict: Estatísticas de vendas
        """
        data = PurchaseManager._load_purchases()
        
        total_purchases = 0
        total_revenue = 0.0
        total_items_sold = 0
        payment_methods = {}
        products_sold = {}
        
        for purchases in data["purchases"].values():
            for purchase in purchases:
                total_purchases += 1
                total_revenue += purchase.get("pricing", {}).get("final_price", 0.0)
                total_items_sold += purchase.get("quantity", 0)
                
                # Contar métodos de pagamento
                method = purchase.get("payment", {}).get("method", "unknown")
                payment_methods[method] = payment_methods.get(method, 0) + 1
                
                # Contar produtos vendidos (incluindo pagamentos genéricos)
                product_id = purchase.get("product", {}).get("id", "unknown")
                product_name = purchase.get("product", {}).get("name", "Unknown")
                
                if product_id not in products_sold:
                    products_sold[product_id] = {
                        "name": product_name,
                        "count": 0,
                        "revenue": 0.0
                    }
                products_sold[product_id]["count"] += 1
                products_sold[product_id]["revenue"] += purchase.get("pricing", {}).get("final_price", 0.0)
        
        return {
            "total_purchases": total_purchases,
            "total_revenue": total_revenue,
            "total_items_sold": total_items_sold,
            "unique_customers": len(data["purchases"]),
            "average_ticket": total_revenue / total_purchases if total_purchases > 0 else 0.0,
            "payment_methods": payment_methods,
            "products_sold": products_sold
        }
    
    @staticmethod
    def get_user_statistics(user_id: int) -> Dict:
        """
        Calcula estatísticas de compras de um usuário específico
        
        Args:
            user_id: ID do usuário
        
        Returns:
            Dict: Estatísticas do usuário
        """
        purchases = PurchaseManager.get_user_purchases(user_id)
        
        total_spent = 0.0
        total_items = 0
        products_bought = {}
        
        for purchase in purchases:
            total_spent += purchase.get("pricing", {}).get("final_price", 0.0)
            total_items += purchase.get("quantity", 0)
            
            product_id = purchase.get("product", {}).get("id", "unknown")
            if product_id not in products_bought:
                products_bought[product_id] = {
                    "name": purchase.get("product", {}).get("name", "Unknown"),
                    "count": 0,
                    "spent": 0.0
                }
            products_bought[product_id]["count"] += 1
            products_bought[product_id]["spent"] += purchase.get("pricing", {}).get("final_price", 0.0)
        
        return {
            "total_purchases": len(purchases),
            "total_spent": total_spent,
            "total_items": total_items,
            "products_bought": products_bought,
            "first_purchase": purchases[-1].get("timestamp") if purchases else None,
            "last_purchase": purchases[0].get("timestamp") if purchases else None
        }
