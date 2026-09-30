import os
from disnake.ext import commands

def setup(bot):
    bot.load_extension("modules.protection.privatizacoes.cog")

    privatizacoes_path = "modules/protection/privatizacoes"
    for module in os.listdir(privatizacoes_path):
        module_path = os.path.join(privatizacoes_path, module)
        if os.path.isdir(module_path) and "__pycache__" not in module:
            cog_path = f"modules.protection.privatizacoes.{module}.cog"
            try:
                bot.load_extension(cog_path)
            except commands.errors.NoEntryPointError:
                pass
            except Exception as e:
                print(f"Failed to load extension {cog_path}: {e}")

__all__ = ["setup"]