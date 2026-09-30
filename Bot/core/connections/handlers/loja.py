"""
Loja module handlers for WebSocket
"""

import logging
from typing import Dict, Any
from functions.database import database as db

logger = logging.getLogger(__name__)

def register_loja_handlers():
    """Register all loja-related handlers"""
    
    async def get_config(bot, payload: dict) -> dict:
        """Get shop configuration"""
        try:
            config = db.get_document("loja_config") or {}
            return {
                'config': config,
                'enabled': config.get('enabled', False)
            }
        except Exception as e:
            logger.error(f"Error getting loja config: {e}")
            raise
    
    async def update_config(bot, payload: dict) -> dict:
        """Update shop configuration"""
        try:
            config = payload.get('config', {})
            db.save_document("loja_config", config)
            return {'success': True, 'message': 'Configuration updated'}
        except Exception as e:
            logger.error(f"Error updating loja config: {e}")
            raise
    
    async def get_products(bot, payload: dict) -> dict:
        """Get all products"""
        try:
            products = db.get_document("loja_products") or {}
            return {
                'products': list(products.values()),
                'count': len(products)
            }
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            raise
    
    async def get_product(bot, payload: dict) -> dict:
        """Get specific product"""
        try:
            product_id = payload.get('productId')
            if not product_id:
                raise ValueError("productId is required")
            
            products = db.get_document("loja_products") or {}
            product = products.get(product_id)
            
            if not product:
                raise ValueError(f"Product {product_id} not found")
            
            return {'product': product}
        except Exception as e:
            logger.error(f"Error getting product: {e}")
            raise
    
    async def create_product(bot, payload: dict) -> dict:
        """Create new product"""
        try:
            product_data = payload.get('productData')
            if not product_data:
                raise ValueError("productData is required")
            
            products = db.get_document("loja_products") or {}
            
            # Generate product ID
            product_id = str(len(products) + 1)
            product_data['id'] = product_id
            
            # Save product
            products[product_id] = product_data
            db.save_document("loja_products", products)
            
            return {
                'success': True,
                'productId': product_id,
                'message': 'Product created successfully'
            }
        except Exception as e:
            logger.error(f"Error creating product: {e}")
            raise
    
    async def update_product(bot, payload: dict) -> dict:
        """Update product"""
        try:
            product_id = payload.get('productId')
            product_data = payload.get('productData')
            
            if not product_id or not product_data:
                raise ValueError("productId and productData are required")
            
            products = db.get_document("loja_products") or {}
            
            if product_id not in products:
                raise ValueError(f"Product {product_id} not found")
            
            # Update product
            products[product_id].update(product_data)
            db.save_document("loja_products", products)
            
            return {
                'success': True,
                'message': 'Product updated successfully'
            }
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            raise
    
    async def delete_product(bot, payload: dict) -> dict:
        """Delete product"""
        try:
            product_id = payload.get('productId')
            if not product_id:
                raise ValueError("productId is required")
            
            products = db.get_document("loja_products") or {}
            
            if product_id not in products:
                raise ValueError(f"Product {product_id} not found")
            
            # Delete product
            del products[product_id]
            db.save_document("loja_products", products)
            
            return {
                'success': True,
                'message': 'Product deleted successfully'
            }
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            raise
    
    async def get_carts(bot, payload: dict) -> dict:
        """Get active carts"""
        try:
            carts = db.get_document("carts") or {}
            active_carts = [
                cart for cart in carts.values()
                if cart.get('status') in ['pending', 'processing']
            ]
            
            return {
                'carts': active_carts,
                'count': len(active_carts)
            }
        except Exception as e:
            logger.error(f"Error getting carts: {e}")
            raise
    
    async def get_orders(bot, payload: dict) -> dict:
        """Get orders history"""
        try:
            filters = payload.get('filters', {})
            orders = db.get_document("orders") or {}
            
            # Apply filters
            filtered_orders = []
            for order in orders.values():
                # Filter by status
                if filters.get('status') and order.get('status') != filters['status']:
                    continue
                
                # Filter by date range
                if filters.get('startDate'):
                    # TODO: Implement date filtering
                    pass
                
                filtered_orders.append(order)
            
            return {
                'orders': filtered_orders,
                'count': len(filtered_orders)
            }
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            raise
    
    async def get_payment_methods(bot, payload: dict) -> dict:
        """Get payment methods"""
        try:
            payment_configs = db.get_document("payment_configs") or {}
            pagamentos = db.get_document("pagamentos") or {}
            
            methods = []
            for method, config in payment_configs.items():
                methods.append({
                    'method': method,
                    'enabled': pagamentos.get(method, False),
                    'configured': bool(config)
                })
            
            return {'methods': methods}
        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            raise
    
    async def update_payment_method(bot, payload: dict) -> dict:
        """Update payment method"""
        try:
            method = payload.get('method')
            config = payload.get('config')
            
            if not method:
                raise ValueError("method is required")
            
            payment_configs = db.get_document("payment_configs") or {}
            payment_configs[method] = config
            db.save_document("payment_configs", payment_configs)
            
            return {
                'success': True,
                'message': f'Payment method {method} updated'
            }
        except Exception as e:
            logger.error(f"Error updating payment method: {e}")
            raise
    
    return {
        'loja.getConfig': get_config,
        'loja.updateConfig': update_config,
        'loja.getProducts': get_products,
        'loja.getProduct': get_product,
        'loja.createProduct': create_product,
        'loja.updateProduct': update_product,
        'loja.deleteProduct': delete_product,
        'loja.getCarts': get_carts,
        'loja.getOrders': get_orders,
        'loja.getPaymentMethods': get_payment_methods,
        'loja.updatePaymentMethod': update_payment_method
    }
