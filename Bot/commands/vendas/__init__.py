from disnake.ext import commands
from . import cupom_em_massa, entregar, perfil, ranking, sincronizar_clientes, afiliados, vip
from . import gerenciar_assinatura, gerenciar_produto, gerenciar_estoque, gerar_pagamento,  aprovar 
from .redeemer import GiftRedeemerCog

def setup(bot: commands.Bot):
    """Carrega todos os comandos de vendas"""
    cupom_em_massa.setup(bot)
    entregar.setup(bot)
    perfil.setup(bot)
    ranking.setup(bot)
    sincronizar_clientes.setup(bot)
    afiliados.setup(bot)
    vip.setup(bot)
    gerenciar_assinatura.setup(bot)
    gerenciar_produto.setup(bot)
    gerenciar_estoque.setup(bot)
    gerar_pagamento.setup(bot)
    aprovar.setup(bot)
    bot.add_cog(GiftRedeemerCog(bot))
