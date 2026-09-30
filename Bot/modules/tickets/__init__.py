from .config.cog import TicketConfigCog
from .functions import setup as functions_setup

def setup(bot):
    bot.add_cog(TicketConfigCog(bot))
    functions_setup(bot)

__all__ = ["setup"]