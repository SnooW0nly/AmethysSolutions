import disnake

from functions.database import database as db
from modules.loja.cart.stock_manager import StockManager

KEY_PRODUCTS = "loja_products"


def clear_stock(product_id: str, field_id: str) -> None:
    # Verificar se é estoque infinito antes de limpar
    products = db.get_document("loja_products")
    product = (products or {}).get(product_id) or {}
    campos = product.get("campos") or {}
    field = campos.get(field_id) or {}
    
    # Se for estoque infinito, remove a configuração de infinito
    if field.get("infinite_stock", {}).get("enabled"):
        del field["infinite_stock"]
        
        # Atualizar stock_info para refletir que não é mais infinito
        stock_info = field.get("stock_info") or {}
        stock_info["is_infinite"] = False
        stock_info["last"] = int(disnake.utils.utcnow().timestamp())
        field["stock_info"] = stock_info
    else:
        # Limpar estoque no database centralizado apenas se não for infinito
        stock = StockManager._load_stock()
        if product_id in stock and field_id in stock[product_id]:
            stock[product_id][field_id] = []
            StockManager._save_stock(stock)
        
        # Atualizar timestamp no products
        stock_info = field.get("stock_info") or {}
        stock_info["last"] = int(disnake.utils.utcnow().timestamp())
        field["stock_info"] = stock_info
    
    campos[field_id] = field
    product["campos"] = campos
    products[product_id] = product
    db.save_document("loja_products", products)


