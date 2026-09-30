# modules/utilitarios/comunidade/familia/commands/__init__.py
from .vpf import setup as setup_vpf


def setup(bot):
    setup_vpf(bot)