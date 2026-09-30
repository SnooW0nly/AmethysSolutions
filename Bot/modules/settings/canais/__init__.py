from .cog import ConfigurarCanais
from .criar_todos import CriarTodosCanais
from .configurar import ConfigurarCanal

def setup(bot):
    bot.add_cog(ConfigurarCanais(bot))
    bot.add_cog(CriarTodosCanais(bot))
    bot.add_cog(ConfigurarCanal(bot))

__all__ = ["setup"]