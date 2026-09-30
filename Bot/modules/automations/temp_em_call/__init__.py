from .cog import TempCallConfig


def setup(bot):
    bot.add_cog(TempCallConfig(bot))