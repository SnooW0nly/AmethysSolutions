# modules/utilitarios/comunidade/conversor/__init__.py
from .cog import ConversorCog


def setup(bot):
    bot.add_cog(ConversorCog(bot))


__all__ = ["setup"]