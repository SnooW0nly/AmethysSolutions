# modules/utilitarios/comunidade/reputacao/__init__.py
from .cog import ReputacaoCog


def setup(bot):
    bot.add_cog(ReputacaoCog(bot))


__all__ = ["setup"]