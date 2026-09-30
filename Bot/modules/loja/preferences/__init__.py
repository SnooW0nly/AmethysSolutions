from disnake.ext import commands
from . import cog as preferences_cog
from . import temp_cart
from . import horario
from . import manutencao
from . import terms
from . import transcripts
from . import solicitar_estoque
from . import notificar_restock
from . import cinco_estrelas
from . import recompensa_feedback
from . import ranking_publico

def setup(bot: commands.Bot):
    """Registra todos os cogs de preferências"""
    preferences_cog.setup(bot)
    temp_cart.setup(bot)
    horario.setup(bot)
    manutencao.setup(bot)
    terms.setup(bot)
    transcripts.setup(bot)
    solicitar_estoque.setup(bot)
    notificar_restock.setup(bot)
    cinco_estrelas.setup(bot)
    recompensa_feedback.setup(bot)
    ranking_publico.setup(bot)

__all__ = ["setup"]

