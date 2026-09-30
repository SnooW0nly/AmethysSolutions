import disnake
from disnake.ext import commands

EXTENSIONS_TASKS = [
    "tasks.extensions.tsk_apostadoff",
]

class ExtensionsTasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        for task_module in EXTENSIONS_TASKS:
            try:
                self.bot.reload_extension(task_module)
            except commands.ExtensionNotLoaded:
                try:
                    self.bot.load_extension(task_module)
                except Exception as e:
                    print(f"Falha ao carregar a tarefa de automação '{task_module}': {e}")
            except Exception as e:
                print(f"Falha ao recarregar a tarefa de automação '{task_module}': {e}")

def setup(bot: commands.Bot):
    bot.add_cog(ExtensionsTasksCog(bot))
  