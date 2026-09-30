# Sistema de Saldo
from disnake.ext import commands
from .cog import SaldoSystem
from .deposit_panel.deposit_handler import DepositHandler
from .checkout_integration import SaldoCheckoutIntegration

def setup(bot: commands.Bot):
    bot.add_cog(SaldoSystem(bot))
    bot.add_cog(DepositHandler(bot))
    bot.add_cog(SaldoCheckoutIntegration(bot))

__all__ = ['SaldoSystem', 'DepositHandler', 'SaldoCheckoutIntegration', 'setup']
