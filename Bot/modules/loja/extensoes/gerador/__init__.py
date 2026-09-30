from disnake.ext import commands
from .cog_painel import GeradorPainelCog
from .cog_servicos import GeradorServicosCog
from .cog_estoque import GeradorEstoqueCog
from .cog_triggers import GeradorTriggersCog
from .cog_runtime import GeradorRuntimeCog


def setup(bot: commands.Bot):
    bot.add_cog(GeradorPainelCog(bot))
    bot.add_cog(GeradorServicosCog(bot))
    bot.add_cog(GeradorEstoqueCog(bot))
    bot.add_cog(GeradorTriggersCog(bot))
    bot.add_cog(GeradorRuntimeCog(bot))


__all__ = ["setup"]