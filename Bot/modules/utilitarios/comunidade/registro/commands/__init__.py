from .registrar import setup as setup_registrar
from .registros import setup as setup_registros

def setup(bot):
    setup_registrar(bot)
    setup_registros(bot)