from disnake.ext import commands
from .buy_modal import BuyProductButton
from .cancel import CancelCheckout
from .cleanup import CartCleanup
from .copy_handler import CopyProductHandler
from .cart_handlers import CartButtonHandlers
from .roles_temp_manager import RolesTempManager
from .members_cart import MembersCartHandlers

def setup(bot: commands.Bot):
    bot.add_cog(BuyProductButton(bot))
    bot.add_cog(CancelCheckout(bot))
    bot.add_cog(CartCleanup(bot))
    bot.add_cog(CopyProductHandler(bot))
    bot.add_cog(CartButtonHandlers(bot))
    bot.add_cog(RolesTempManager(bot))
    bot.add_cog(MembersCartHandlers(bot))

__all__ = ["setup"]