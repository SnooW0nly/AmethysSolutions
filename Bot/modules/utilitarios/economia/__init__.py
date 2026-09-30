from .cog import EconomyCog

def setup(bot):
    bot.add_cog(EconomyCog(bot))

__all__ = ["setup"]