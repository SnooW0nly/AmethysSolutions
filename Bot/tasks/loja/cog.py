import disnake
from disnake.ext import commands

LOJA_TASKS = [
    # ── Loja ──────────────────────────────────────────────
    "tasks.loja.tsk_afiliados",         # ← NOVO
    "tasks.loja.tsk_calculadora_roblox", # ← Calculadora de Robux
    "tasks.loja.tsk_assinaturas",        # ← Assinaturas VIP
    "tasks.loja.tsk_ranking_publico",
    "tasks.loja.tsk_marketplace_cache", 
]

class LojaTasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        for task_module in LOJA_TASKS:
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
    bot.add_cog(LojaTasksCog(bot))