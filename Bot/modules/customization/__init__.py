from .cog import Personalizacao
from .edit_mode import EditMode
from .edit_colors import EditColorsCog
from .edit_emojis import EditEmojisCog
from .edit_bio import EditBioCog

def setup(bot):
    bot.add_cog(Personalizacao(bot))
    bot.add_cog(EditColorsCog(bot))
    bot.add_cog(EditEmojisCog(bot))

__all__ = ["setup"]