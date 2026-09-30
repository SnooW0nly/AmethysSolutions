"""
Sistema unificado de validação de cupons
Suporta cupons de produto e cupons em massa
"""
import disnake
from datetime import datetime
from typing import Optional, Tuple
from functions.database import database as db


class CouponValidator:
    """Validador unificado de cupons"""
    
    @staticmethod
    def validate_product_coupon(
        coupon_code: str,
        product_id: str,
        user_id: int,
        purchase_value: float
    ) -> Tuple[bool, str, float, Optional[dict]]:
        """
        Valida um cupom de produto específico
        Returns: (is_valid, error_message, discount_amount, coupon_data)
        """
        products = db.get_document("loja_products") or {}
        product = products.get(product_id, {})
        cupons = product.get("cupons", {})
        
        # Buscar cupom por nome (case insensitive)
        coupon_code_upper = coupon_code.upper()
        coupon_data = None
        coupon_id = None
        
        for cid, cdata in cupons.items():
            if cdata.get("name", "").upper() == coupon_code_upper:
                coupon_data = cdata
                coupon_id = cid
                break
        
        if not coupon_data:
            return False, "Cupom não encontrado para este produto", 0, None
        
        # Verificar se está ativo
        if not coupon_data.get("active", True):
            return False, "Cupom desativado", 0, None
        
        # Verificar expiração
        expires_at = coupon_data.get("expires_at")
        if expires_at:
            now_ts = int(datetime.now().timestamp())
            if now_ts > expires_at:
                return False, "Cupom expirado", 0, None
        
        # Verificar máximo de usos
        max_uses = coupon_data.get("max_uses")
        if max_uses is not None and max_uses > 0:
            uses_count = coupon_data.get("uses_count", 0)
            if uses_count >= max_uses:
                return False, "Cupom esgotado", 0, None
        
        # Verificar valor mínimo do carrinho
        min_cart = coupon_data.get("min_cart")
        if min_cart is not None and min_cart > 0:
            if purchase_value < min_cart:
                return False, f"Valor mínimo: R$ {min_cart:.2f}", 0, None
        
        # Verificar valor máximo do carrinho
        max_cart = coupon_data.get("max_cart")
        if max_cart is not None and max_cart > 0:
            if purchase_value > max_cart:
                return False, f"Valor máximo: R$ {max_cart:.2f}", 0, None
        
        # Calcular desconto (porcentagem)
        percent = coupon_data.get("percent", 0)
        discount = purchase_value * (percent / 100)
        
        # Não deixar desconto maior que o valor da compra
        discount = min(discount, purchase_value)
        
        return True, "", discount, coupon_data
    
    @staticmethod
    def validate_mass_coupon(
        coupon_code: str,
        user_id: int,
        purchase_value: float,
        guild: disnake.Guild
    ) -> Tuple[bool, str, float, Optional[dict]]:
        """
        Valida um cupom em massa
        Returns: (is_valid, error_message, discount_amount, coupon_data)
        """
        data = db.get_document("loja_mass_coupons") or {}
        coupons = data.get("coupons", {})
        
        code_upper = coupon_code.upper()
        if code_upper not in coupons:
            return False, "Cupom não encontrado", 0, None
        
        coupon = coupons[code_upper]
        
        # Verificar expiração
        if coupon.get("expiration"):
            if datetime.now().timestamp() > coupon["expiration"]:
                return False, "Cupom expirado", 0, None
        
        # Verificar máximo de usos
        if coupon.get("max_uses", 0) > 0:
            if coupon.get("uses", 0) >= coupon["max_uses"]:
                return False, "Cupom esgotado", 0, None
        
        # Verificar se usuário já usou
        if user_id in coupon.get("used_by", []):
            return False, "Você já usou este cupom", 0, None
        
        # Verificar valor mínimo
        if coupon.get("min_purchase", 0) > 0:
            if purchase_value < coupon["min_purchase"]:
                return False, f"Compra mínima: R$ {coupon['min_purchase']:.2f}", 0, None
        
        # Verificar valor máximo
        if coupon.get("max_purchase"):
            if purchase_value > coupon["max_purchase"]:
                return False, f"Compra máxima: R$ {coupon['max_purchase']:.2f}", 0, None
        
        # Verificar cargo obrigatório
        if coupon.get("required_role"):
            member = guild.get_member(user_id)
            if member:
                role = guild.get_role(coupon["required_role"])
                if role and role not in member.roles:
                    return False, f"Cargo obrigatório: {role.name}", 0, None
            else:
                return False, "Membro não encontrado", 0, None
        
        # Calcular desconto
        if coupon.get("discount_type") == "porcentagem":
            discount = purchase_value * (coupon.get("discount_value", 0) / 100)
            if coupon.get("max_discount"):
                discount = min(discount, coupon["max_discount"])
        else:
            discount = coupon.get("discount_value", 0)
        
        # Não deixar desconto maior que o valor da compra
        discount = min(discount, purchase_value)
        
        return True, "", discount, coupon
    
    @staticmethod
    def validate_coupon(
        coupon_code: str,
        product_id: str,
        user_id: int,
        purchase_value: float,
        guild: disnake.Guild
    ) -> Tuple[bool, str, float, str, Optional[dict]]:
        """
        Valida um cupom (tenta produto primeiro, depois massa)
        Returns: (is_valid, error_message, discount_amount, coupon_type, coupon_data)
        coupon_type: 'product' ou 'mass'
        """
        # Tentar cupom de produto primeiro
        is_valid, error_msg, discount, coupon_data = CouponValidator.validate_product_coupon(
            coupon_code, product_id, user_id, purchase_value
        )
        
        if is_valid:
            return True, "", discount, "product", coupon_data
        
        # Se não encontrou cupom de produto, tentar cupom em massa
        is_valid, error_msg, discount, coupon_data = CouponValidator.validate_mass_coupon(
            coupon_code, user_id, purchase_value, guild
        )
        
        if is_valid:
            return True, "", discount, "mass", coupon_data
        
        # Nenhum cupom válido encontrado
        return False, error_msg, 0, "", None
    
    @staticmethod
    def use_product_coupon(product_id: str, coupon_code: str, user_id: int):
        """Marca o cupom de produto como usado"""
        products = db.get_document("loja_products") or {}
        product = products.get(product_id, {})
        cupons = product.get("cupons", {})
        
        coupon_code_upper = coupon_code.upper()
        
        for cid, cdata in cupons.items():
            if cdata.get("name", "").upper() == coupon_code_upper:
                cupons[cid]["uses_count"] = cupons[cid].get("uses_count", 0) + 1
                cupons[cid]["updated_at"] = int(datetime.now().timestamp())
                product["cupons"] = cupons
                products[product_id] = product
                db.save_document("loja_products", products)
                break
    
    @staticmethod
    def use_mass_coupon(coupon_code: str, user_id: int):
        """Marca o cupom em massa como usado"""
        data = db.get_document("loja_mass_coupons") or {}
        code_upper = coupon_code.upper()
        
        if code_upper in data.get("coupons", {}):
            data["coupons"][code_upper]["uses"] = data["coupons"][code_upper].get("uses", 0) + 1
            if user_id not in data["coupons"][code_upper].get("used_by", []):
                data["coupons"][code_upper].setdefault("used_by", []).append(user_id)
            db.save_document("loja_mass_coupons", data)
    
    @staticmethod
    def use_coupon(coupon_code: str, coupon_type: str, product_id: str, user_id: int):
        """Marca o cupom como usado (produto ou massa)"""
        if coupon_type == "product":
            CouponValidator.use_product_coupon(product_id, coupon_code, user_id)
        elif coupon_type == "mass":
            CouponValidator.use_mass_coupon(coupon_code, user_id)
    
    @staticmethod
    def is_free_coupon(discount_amount: float, total_price: float) -> bool:
        """Verifica se o cupom torna a compra gratuita (100% de desconto)"""
        return discount_amount >= total_price and total_price > 0
