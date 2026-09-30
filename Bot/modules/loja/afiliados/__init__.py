"""
Módulo de personalização da loja
"""

def setup(bot):
    from .cog import AfiliadosCog
  
    bot.add_cog(AfiliadosCog(bot))