"""
Módulo de personalização da loja
"""

def setup(bot):
    from .cog import PersonalizarLoja
    from .mensagens.cog import PersonalizarMensagens
    from .sales_logs_customization import SalesLogsCog
    
    bot.add_cog(PersonalizarLoja(bot))
    bot.add_cog(PersonalizarMensagens(bot))
    bot.add_cog(SalesLogsCog(bot))