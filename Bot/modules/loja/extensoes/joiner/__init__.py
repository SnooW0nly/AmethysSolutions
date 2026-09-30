from disnake.ext import commands
from .cog_painel import JoinerPainelCog
from .cog_runtime import JoinerRuntimeCog
from .cog_oauth import JoinerOAuthCog
from .cog_gifts import JoinerGiftsCog
from .cog_boost import JoinerBoostCog
from .cog_keys import JoinerKeysCog
from .websocket_manager import get_websocket_manager

def setup(bot: commands.Bot):
    bot.add_cog(JoinerPainelCog(bot))
    bot.add_cog(JoinerRuntimeCog(bot))
    bot.add_cog(JoinerOAuthCog(bot))
    bot.add_cog(JoinerGiftsCog(bot))
    bot.add_cog(JoinerBoostCog(bot))
    bot.add_cog(JoinerKeysCog(bot))

    # WebSocket agora é inicializado centralmente no events/on_ready.py
    pass

__all__ = ["setup"]
