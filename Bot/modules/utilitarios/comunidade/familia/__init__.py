# modules/utilitarios/comunidade/familia/__init__.py
from .cog import FamiliaCog
from .commands import setup as setup_commands


def setup(bot):
    bot.add_cog(FamiliaCog(bot))
    setup_commands(bot)


__all__ = ["setup"]