from .automations import setup as automations_setup
from .customization import setup as customization_setup
from .loja import setup as loja_setup
from .protection import setup as protection_setup
from .settings import setup as settings_setup
from .tickets import setup as tickets_setup
from .giveaways import setup as giveaways_setup
from .cloud import setup as cloud_setup
from functions.plan import should_load_module
from .telegram import setup as telegram_setup
#from .rendimentos import setup as rendimentos_setup
from .utilitarios import setup as utilitarios_setup
from .utilitarios.tools.cog import setup as tools_setup
# from .utilitarios.parcerias import setup as parcerias_setup
from .utilitarios.apostadoff import setup as apostadoff_setup 


def setup(bot):
    telegram_setup(bot)
    # Carrega módulos baseado no plano configurado
    if should_load_module("automations"):
        automations_setup(bot)
    if should_load_module("customization"):
        customization_setup(bot)
    if should_load_module("loja"):
        loja_setup(bot)
    #if should_load_module("rendimentos"):
        #rendimentos_setup(bot)
    if should_load_module("protection"):
        protection_setup(bot)
    if should_load_module("settings"):
        settings_setup(bot)
    if should_load_module("tickets"):
        tickets_setup(bot)
    if should_load_module("giveaways"):
        giveaways_setup(bot)
    if should_load_module("cloud"):
        cloud_setup(bot)
    if should_load_module("utilitarios"):
        utilitarios_setup(bot)
        tools_setup(bot)
   #     parcerias_setup(bot)
        apostadoff_setup(bot)
      
__all__ = ["setup"]