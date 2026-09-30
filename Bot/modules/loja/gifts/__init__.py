from disnake.ext import commands
from .cog import GiftsCog
from .message_editor import GiftMessageEditorCog
from .manager import GiftManagerCog
from .sender import GiftSenderCog


def setup(bot: commands.Bot):
    bot.add_cog(GiftsCog(bot))
    bot.add_cog(GiftMessageEditorCog(bot))
    bot.add_cog(GiftManagerCog(bot))
    bot.add_cog(GiftSenderCog(bot))


__all__ = ["setup"]