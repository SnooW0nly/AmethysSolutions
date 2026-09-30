from disnake.ext import commands
from .cog import EcommerceCog


def setup(bot: commands.Bot):
    bot.add_cog(EcommerceCog(bot))
    # O ws_bridge do Marketplace agora vive em connections/ws_bridge.py
    # e é inicializado pelo on_ready junto com as demais conexões WebSocket.


__all__ = ["setup"]