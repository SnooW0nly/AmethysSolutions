from disnake.ext import commands
from .admin import anunciar, painel, backup, function_payment
from .mod import mod
from . import tickets
from . import contextmenus
from . import giveaways
from . import vendas
#from . import extensions
from functions.plan import should_load_command, should_load_module

def setup(bot: commands.Bot):
    # Carrega comandos baseado no plano configurado
    if should_load_command("anunciar"):
        anunciar.setup(bot)
    if should_load_command("painel"):
        painel.setup(bot)
    if should_load_command("function_payment"):
        function_payment.setup(bot)
    if should_load_command("mod"):
        mod.setup(bot)
    if should_load_command("tickets"):
        tickets.setup(bot)
    if should_load_command("backup"):
        backup.setup(bot)
    if should_load_command("contextmenus"):
        contextmenus.setup(bot)
    if should_load_command("giveaways"):
        giveaways.setup(bot)
    if should_load_module("loja"):
        vendas.setup(bot)
    
    # Carregar comandos de extensões
    #extensions.setup(bot)