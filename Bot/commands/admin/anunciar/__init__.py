from disnake.ext import commands

from .components.buttons import Buttons
from .components.container import Container
from .components.embed import Embed
from .components.helper import Helper
from .components.images import Images
from .components.message import Message
from .components.selects import Selects
from .components.importar import Importar        
from .components.audio import Audio    
from .anunciar import Anunciar
from .preview import Preview
from .enviar import Enviar
from .template import Templates
from .telegram import TelegramAnunciar


def setup(bot: commands.Bot) -> None:
    bot.add_cog(Templates(bot))
    bot.add_cog(Anunciar(bot))
    bot.add_cog(Message(bot))
    bot.add_cog(Container(bot))
    bot.add_cog(Embed(bot))
    bot.add_cog(Helper(bot))
    bot.add_cog(Images(bot))
    bot.add_cog(Buttons(bot))
    bot.add_cog(Selects(bot))
    bot.add_cog(Preview(bot))
    bot.add_cog(Enviar(bot))
    bot.add_cog(Importar(bot))
    bot.add_cog(Audio(bot))
    bot.add_cog(TelegramAnunciar(bot))

__all__ = ["setup"]