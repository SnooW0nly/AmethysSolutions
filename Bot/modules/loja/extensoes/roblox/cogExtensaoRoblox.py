"""
cogExtensaoRoblox.py
--------------------
Este módulo NÃO possui listeners de interação.

O hub de extensões (modules/settings/extensions/cog.py) é o único responsável
por responder à interação 'Extensions_Select'. Quando o hub roteia para 'roblox',
ele importa get_roblox_main_panel() daqui e responde com
inter.response.edit_message() — sem nenhum outro cog interferindo.

Ter qualquer listener de on_dropdown / on_message_interaction aqui que também
trate Extensions_Select causaria erro 40060 (Interaction already acknowledged).
"""

from disnake.ext import commands

# Re-exporta para facilitar import pelo hub
from .paineis import get_roblox_main_panel  # noqa: F401


def setup(bot: commands.Bot) -> None:
    # Sem Cog — apenas garante que o módulo seja carregado corretamente.
    pass