"""
Sistema de logs de pedidos e eventos de compra
"""

def setup(bot):
    from .purchase_logs import PurchaseLogsSystem
    bot.add_cog(PurchaseLogsSystem(bot))
