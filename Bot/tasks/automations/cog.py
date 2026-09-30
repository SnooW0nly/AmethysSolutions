import disnake
from disnake.ext import commands

AUTOMATION_TASKS = [
    "tasks.automations.tsk_boas_vindas",
    "tasks.automations.tsk_clean",
    "tasks.automations.tsk_cont_members",
    "tasks.automations.tsk_cont_members_call",
    "tasks.automations.tsk_cont_vendas",
    "tasks.automations.tsk_invite_tracker",
    "tasks.automations.tsk_lock_unlock",
    "tasks.automations.tsk_msg_auto",
    "tasks.automations.tsk_reactions",
    "tasks.automations.tsk_response_auto",
    "tasks.automations.tsk_suggestions",
    "tasks.automations.tsk_topics",
    "tasks.automations.tsk_nuke",
    "tasks.automations.tsk_repost",
    "tasks.automations.close_tickets",
    "tasks.automations.tsk_instagram",
    "tasks.automations.tsk_cont_feedbacks",
    "tasks.automations.tsk_keys",
    "tasks.automations.tsk_tempcall",
    "tasks.automations.tsk_random_usernames",
    "tasks.automations.tsk_auto_role_avancado",
    "tasks.automations.tsk_random_gifs"
]


class AutomationTasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._tasks_loaded = False

    @commands.Cog.listener()
    async def on_ready(self):
        # Garante que as extensões sejam carregadas apenas uma vez,
        # mesmo que on_ready dispare múltiplas vezes (ex: reconexões).
        if self._tasks_loaded:
            return
        self._tasks_loaded = True

        for task_module in AUTOMATION_TASKS:
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
    bot.add_cog(AutomationTasksCog(bot))
