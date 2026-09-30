from .cog import ConfigurarCargos
from .criar_todos import CriarTodosCargos
from .configurar import ConfigurarCargo

def setup(bot):
    bot.add_cog(ConfigurarCargos(bot))
    bot.add_cog(CriarTodosCargos(bot))
    bot.add_cog(ConfigurarCargo(bot))

__all__ = ["setup"]