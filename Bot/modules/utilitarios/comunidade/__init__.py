from .cog import ComunidadeCog

def setup(bot):
    bot.add_cog(ComunidadeCog(bot))

__all__ = ["setup"]