import disnake
from disnake.ext import commands

from functions.database import database as db
from tasks.giveaways import roll_giveaways
from modules.giveaways.cog import Giveaways
from modules.giveaways.config_tasks import RepostConfirmationView_components, RepostConfirmationView_embed
from functions.perms import perms
from functions.emoji import emoji


def create_giveaway_autocomplete(status_filter: tuple):
    async def autocomplete(inter: disnake.ApplicationCommandInteraction, user_input: str):
        giveaways = db.obter("database/giveaways/giveaways_data.json") or {}
        choices = {}
        
        for giveaway_id, giveaway in giveaways.items():
            for task in giveaway.get("tasks", []):
                if task.get("status") in status_filter:
                    name = f"{giveaway.get('name', 'Sorteio')} - {task.get('name', 'Tarefa')}"
                    if user_input.lower() in name.lower():
                        choices[name] = f"{giveaway_id}/{task['id']}"

        return {k: v for i, (k, v) in enumerate(choices.items()) if i < 25}
    return autocomplete

autocomplete_reroll = create_giveaway_autocomplete(("finished",))
autocomplete_end = create_giveaway_autocomplete(("running",))
autocomplete_info = create_giveaway_autocomplete(("running", "finished", "pending", "error"))
autocomplete_repost = create_giveaway_autocomplete(("finished","error"))
autocomplete_send = create_giveaway_autocomplete(("pending", "running"))


class GiveawayCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="giveaway",
        description="Gerencia os sorteios.",
        guild_ids=[int(db.obter("config.json")["bot"]["server"])],
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def giveaway(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @giveaway.sub_command(name="reroll", description="Sorteia novamente os ganhadores de um sorteio finalizado.")
    async def reroll(
        self,
        inter: disnake.ApplicationCommandInteraction,
        giveaway_task: str = commands.Param(description="Selecione o sorteio para sortear novamente", autocomplete=autocomplete_reroll)
    ):
        if not await perms.check(inter.user.id):
            await inter.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            return
        
        await inter.response.defer(ephemeral=True)
        giveaway_id, task_id = giveaway_task.split("/")
        await roll_giveaways.process_giveaway_roll(self.bot, giveaway_id, task_id, is_reroll=True)
        await inter.edit_original_message(content=f"{emoji.correct} O sorteio foi realizado novamente com sucesso!")

    @giveaway.sub_command(name="end", description="Finaliza um sorteio em andamento imediatamente.")
    async def end(
        self,
        inter: disnake.ApplicationCommandInteraction,
        giveaway_task: str = commands.Param(description="Selecione o sorteio para finalizar", autocomplete=autocomplete_end)
    ):
        if not await perms.check(inter.user.id):
            await inter.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        giveaway_id, task_id = giveaway_task.split("/")
        await roll_giveaways.process_giveaway_roll(self.bot, giveaway_id, task_id, is_reroll=False)
        await inter.edit_original_message(content=f"{emoji.correct} O sorteio foi finalizado com sucesso!")

    @giveaway.sub_command(name="info", description="Mostra informações detalhadas de um sorteio.")
    async def info(
        self,
        inter: disnake.ApplicationCommandInteraction,
        giveaway_task: str = commands.Param(description="Selecione um sorteio para ver as informações", autocomplete=autocomplete_info)
    ):
        if not await perms.check(inter.user.id):
            await inter.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            return

        giveaway_id, task_id = giveaway_task.split("/")
        giveaways_cog = self.bot.get_cog("Giveaways")
        if not giveaways_cog:
            await inter.response.send_message(content=f"{emoji.wrong} O módulo de sorteios parece estar desativado.", ephemeral=True)
            return

        await inter.response.defer(ephemeral=True)
        
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(giveaway_id)
        task = next((t for t in giveaway.get("tasks", []) if t.get("id") == task_id), None)
        
        await giveaways_cog.show_giveaway_info(inter, giveaway, task, giveaway_id, task_id)

    @giveaway.sub_command(name="send", description="Envia ou reenvia a mensagem de um sorteio.")
    async def send(
        self,
        inter: disnake.ApplicationCommandInteraction,
        giveaway_task: str = commands.Param(description="Selecione o sorteio para enviar/reenviar", autocomplete=autocomplete_send)
    ):
        if not await perms.check(inter.user.id):
            await inter.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            return
        
        await inter.response.defer(ephemeral=True)
        
        giveaway_id, task_id = giveaway_task.split("/")
        
        giveaways_cog = self.bot.get_cog("Giveaways")
        if not giveaways_cog:
            await inter.edit_original_message(content=f"{emoji.wrong} O módulo de sorteios parece estar desativado.")
            return

        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(giveaway_id)
        task = next((t for t in giveaway.get("tasks", []) if t.get("id") == task_id), None)

        if not task:
            await inter.edit_original_message("Tarefa não encontrada.")
            return

        is_resend = False
        if task.get("status") == "running":
            is_resend = True
            if task.get("message_id") and task.get("channel_id"):
                try:
                    channel = await self.bot.fetch_channel(task["channel_id"])
                    message_to_delete = await channel.fetch_message(task["message_id"])
                    await message_to_delete.delete()
                except (disnake.NotFound, disnake.Forbidden):
                    pass
        
        await giveaways_cog._send_giveaway_message(inter, giveaway_id, task_id, is_resend=is_resend, refresh_panel=False)

    @giveaway.sub_command(name="repost", description="Reposta um sorteio finalizado.")
    async def repost(
        self,
        inter: disnake.ApplicationCommandInteraction,
        giveaway_task: str = commands.Param(description="Selecione um sorteio para repostar", autocomplete=autocomplete_repost)
    ):
        if not await perms.check(inter.user.id):
            await inter.response.send_message("Você não tem permissão para usar este comando.", ephemeral=True)
            return

        giveaway_id, task_id = giveaway_task.split("/")
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            components = RepostConfirmationView_components(giveaway_id, task_id)
            await inter.response.send_message(components=components, ephemeral=True)
        else:
            embed, components = RepostConfirmationView_embed(giveaway_id, task_id)
            await inter.response.send_message(embed=embed, components=components, ephemeral=True)

def setup(bot):
    bot.add_cog(GiveawayCommands(bot))