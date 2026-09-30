from .cog import RegistroCog
from .commands import setup as setup_commands


def setup(bot):
    bot.add_cog(RegistroCog(bot))
    setup_commands(bot)


__all__ = ["setup"]