from disnake.ext import commands
from .buy_robux import BuyRobuxHandler
from .checkout_robux import CheckoutRobux
from .delivery_robux import DeliveryRobux


def setup(bot: commands.Bot):
    bot.add_cog(BuyRobuxHandler(bot))
    bot.add_cog(CheckoutRobux(bot))
    bot.add_cog(DeliveryRobux(bot))


__all__ = ["setup"]