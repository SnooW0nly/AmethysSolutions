from disnake.ext import commands
from .cogRoblox import CogRoblox
from .cogMensagemRoblox import RobloxMensagemEditor
from .carrinho.buy_robux import BuyRobuxHandler
from .carrinho.checkout_robux import CheckoutRobux
from .carrinho.delivery_robux import DeliveryRobux


def setup(bot: commands.Bot):
    bot.add_cog(CogRoblox(bot))
    bot.add_cog(RobloxMensagemEditor(bot))
    bot.add_cog(BuyRobuxHandler(bot))
    bot.add_cog(CheckoutRobux(bot))
    bot.add_cog(DeliveryRobux(bot))


__all__ = ["setup"]