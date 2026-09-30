from .cog import TagBioCog

def setup(bot):
    bot.add_cog(TagBioCog(bot))

__all__ = ["setup"]