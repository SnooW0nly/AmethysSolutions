import os
from disnake.ext import commands

def setup(bot):
    bot.load_extension("modules.protection.protecaogeral.cog")

    protecao_geral_path = "modules/protection/protecaogeral"
    for module in os.listdir(protecao_geral_path):
        module_path = os.path.join(protecao_geral_path, module)
        if os.path.isdir(module_path) and "__pycache__" not in module:
            cog_path = f"modules.protection.protecaogeral.{module}.cog"
            try:
                bot.load_extension(cog_path)
            except commands.errors.NoEntryPointError:
                pass
            except Exception as e:
                print(f"Failed to load extension {cog_path}: {e}")

__all__ = ["setup"]