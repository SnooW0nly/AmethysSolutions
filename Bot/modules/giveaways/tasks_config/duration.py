import disnake
from functions.database import database as db
from functions.emoji import emoji
import datetime
import time

class DurationModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.Interaction, giveaway_id: str, task_id: str, task_data: dict):
        self.inter = inter
        self.giveaway_id = giveaway_id
        self.task_id = task_id

        start_timestamp = task_data.get("start_time")
        end_timestamp = task_data.get("end_time")

        start_date_str = datetime.datetime.fromtimestamp(start_timestamp).strftime('%d/%m/%Y') if start_timestamp else ""
        start_time_str = datetime.datetime.fromtimestamp(start_timestamp).strftime('%H:%M') if start_timestamp else ""
        end_date_str = datetime.datetime.fromtimestamp(end_timestamp).strftime('%d/%m/%Y') if end_timestamp else ""
        end_time_str = datetime.datetime.fromtimestamp(end_timestamp).strftime('%H:%M') if end_timestamp else ""

        components = [
            disnake.ui.TextInput(
                label="Data de Início",
                custom_id="start_date",
                placeholder="DD/MM/YYYY",
                value=start_date_str,
                max_length=10,
            ),
            disnake.ui.TextInput(
                label="Hora de Início",
                custom_id="start_time",
                placeholder="HH:MM",
                value=start_time_str,
                max_length=5,
            ),
            disnake.ui.TextInput(
                label="Data de Fim",
                custom_id="end_date",
                placeholder="DD/MM/YYYY",
                value=end_date_str,
                max_length=10,
            ),
            disnake.ui.TextInput(
                label="Hora de Fim",
                custom_id="end_time",
                placeholder="HH:MM",
                value=end_time_str,
                max_length=5,
            ),
        ]
        super().__init__(title="Definir Duração da Tarefa", components=components, custom_id=f"duration_modal_{giveaway_id}_{task_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        
        try:
            start_str = f"{inter.text_values['start_date']} {inter.text_values['start_time']}"
            end_str = f"{inter.text_values['end_date']} {inter.text_values['end_time']}"

            start_dt = datetime.datetime.strptime(start_str, "%d/%m/%Y %H:%M")
            end_dt = datetime.datetime.strptime(end_str, "%d/%m/%Y %H:%M")

            start_timestamp = int(time.mktime(start_dt.timetuple()))
            end_timestamp = int(time.mktime(end_dt.timetuple()))

            if end_timestamp <= start_timestamp:
                await inter.followup.send(f"{emoji.wrong} A data/hora de término deve ser posterior à de início.", ephemeral=True)
                return

        except ValueError:
            await inter.followup.send(f"{emoji.wrong} Formato de data ou hora inválido. Use DD/MM/YYYY e HH:MM.", ephemeral=True)
            return

        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id, {})
        if not giveaway:
            await inter.followup.send(f"{emoji.wrong} Erro: Sorteio não encontrado.", ephemeral=True)
            return

        task = next((t for t in giveaway.get("tasks", []) if t.get("id") == self.task_id), None)
        if not task:
            await inter.followup.send(f"{emoji.wrong} Erro: Tarefa não encontrada.", ephemeral=True)
            return

        task["start_time"] = start_timestamp
        task["end_time"] = end_timestamp
        db.salvar("database/giveaways/giveaways_data.json", config)

        from tasks.giveaways.logger_giveaways import log_giveaway_event
        await log_giveaway_event(
            bot=inter.bot,
            giveaway_id=self.giveaway_id,
            title="Sorteios - Configuração de Tarefa Alterada",
            lines=[
                f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                f"{emoji.settings} **Tarefa:** {task.get('name')}",
                f"{emoji.edit} **Duração Definida:** <t:{start_timestamp}:f> a <t:{end_timestamp}:f>",
                f"{emoji.member} **Executor:** {inter.author.mention}"
            ]
        )
        
        await inter.followup.send(f"{emoji.correct} Duração definida com sucesso!", ephemeral=True)

        from ..config_tasks import TaskEditorView_components, TaskEditorView_embed
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await self.inter.edit_original_message(components=TaskEditorView_components(self.inter, self.giveaway_id, self.task_id))
        else:
            embed, components = TaskEditorView_embed(self.inter, self.giveaway_id, self.task_id)
            await self.inter.edit_original_message(content=None, embed=embed, components=components)
