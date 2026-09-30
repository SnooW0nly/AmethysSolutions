from disnake.ext import commands
from .cog import GerenciarProdutos
from .product.create import CreateProduct
from .product.configurar import ConfigurarProduto
from .product.edit import EditProduct
from .product.delete import DeleteProduct
from .product.coupons.cog import GerenciarCupons
from .product.coupons.create import CreateCoupon
from .product.coupons.configurar import ConfigurarCupom
from .product.coupons.actions import CouponActions
from .product.campos.cog import GerenciarCamposCategorias
from .product.campos.fields.modals import FieldModals
from .product.campos.fields.actions import FieldActions
from .product.campos.fields.actions import BoostFieldActions
from .product.campos.fields.configurar import ConfigurarCampo
from .product.campos.fields.integracao_vip import IntegracaoVIPActions
from .product.campos.fields.cargos import setup as setup_cargos
from .product.campos.fields.estoque.cog import EstoqueCampoCog
from .product.send import SendProduct
from .product.extra_button import ExtraButtonCog

def setup(bot: commands.Bot):
    bot.add_cog(GerenciarProdutos(bot))
    bot.add_cog(CreateProduct(bot))
    bot.add_cog(ConfigurarProduto(bot))
    bot.add_cog(EditProduct(bot))
    bot.add_cog(DeleteProduct(bot))
    bot.add_cog(GerenciarCupons(bot))
    bot.add_cog(CreateCoupon(bot))
    bot.add_cog(ConfigurarCupom(bot))
    bot.add_cog(CouponActions(bot))
    bot.add_cog(GerenciarCamposCategorias(bot))
    bot.add_cog(FieldModals(bot))
    bot.add_cog(FieldActions(bot))
    bot.add_cog(BoostFieldActions(bot))
    bot.add_cog(ConfigurarCampo(bot))
    bot.add_cog(IntegracaoVIPActions(bot))
    setup_cargos(bot)
    bot.add_cog(EstoqueCampoCog(bot))
    bot.add_cog(SendProduct(bot))
    bot.add_cog(ExtraButtonCog(bot))
    
__all__ = ["setup"]