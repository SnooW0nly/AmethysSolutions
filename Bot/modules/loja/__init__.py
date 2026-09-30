from disnake.ext import commands
from .cog import Loja
from .products import setup as products_setup
from .cart import setup as cart_setup
from .logs import setup as logs_setup
from .personalization import setup as personalization_setup
from .clientes import setup as clientes_setup
from .preferences import setup as preferences_setup
from .saldo import setup as saldo_setup
from .cashback import setup as cashback_setup
from .afiliados import setup as afiliados_setup  # ← NOVO
from .gifts import setup as gifts_setup
from .ecommerce import setup as ecommerce_setup
from .extensoes import setup as extensoes_setup
from .marketplace import setup as marketplace_setup  # ← NOVO

def setup(bot: commands.Bot):
    bot.add_cog(Loja(bot))
    products_setup(bot)
    cart_setup(bot)
    logs_setup(bot)
    personalization_setup(bot)
    clientes_setup(bot)
    preferences_setup(bot)
    saldo_setup(bot)
    cashback_setup(bot)
    afiliados_setup(bot)
    gifts_setup(bot)
    ecommerce_setup(bot)
    extensoes_setup(bot)
    marketplace_setup(bot)  # ← NOVO

__all__ = ["setup"]