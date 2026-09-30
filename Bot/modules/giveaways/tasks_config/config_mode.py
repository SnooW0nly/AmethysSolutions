import disnake
from functions.emoji import emoji
from ..config_giveaways import get_giveaways
from functions.database import database as db

class KeywordModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.Interaction, giveaway_id: str, task_id: str):
        self.inter = inter
        self.giveaway_id = giveaway_id
        self.task_id = task_id
        
        components = [
            disnake.ui.TextInput(
                label="Palavra/Frase Chave",
                custom_id="keyword",
                style=disnake.TextInputStyle.short,
                placeholder="Ex: eu amo a Sync!",
                required=True,
                max_length=100,
            ),
        ]
        super().__init__(title="Definir Palavra-Chave", components=components)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        keyword = inter.text_values["keyword"]
        
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id)
        if not giveaway:
            await inter.response.send_message(f"{emoji.wrong} Erro: Sorteio não encontrado.", ephemeral=True)
            return

        task = next((t for t in giveaway.get("tasks", []) if t["id"] == self.task_id), None)
        if not task:
            await inter.response.send_message(f"{emoji.wrong} Erro: Tarefa não encontrada.", ephemeral=True)
            return

        task["participation_mode"] = "keyword"
        task["keyword"] = keyword
        db.salvar("database/giveaways/giveaways_data.json", config)
        
        from tasks.giveaways.logger_giveaways import log_giveaway_event
        await log_giveaway_event(
            bot=inter.bot,
            giveaway_id=self.giveaway_id,
            title="Sorteios - Configuração de Tarefa Alterada",
            lines=[
                f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                f"{emoji.settings} **Tarefa:** {task.get('name')}",
                f"{emoji.edit} **Modo de Participação:** Palavra-Chave (`{keyword}`)",
                f"{emoji.member} **Executor:** {inter.author.mention}"
            ]
        )
        
        await inter.response.send_message(f"{emoji.correct} A palavra-chave '{keyword}' foi definida com sucesso!", ephemeral=True)

        from ..config_tasks import TaskEditorView_components, TaskEditorView_embed
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await self.inter.edit_original_message(components=TaskEditorView_components(self.inter, self.giveaway_id, self.task_id))
        else:
            embed, components = TaskEditorView_embed(self.inter, self.giveaway_id, self.task_id)
            await self.inter.edit_original_message(content=None, embed=embed, components=components)


def ModeSelectView_components(giveaway_id: str, task_id: str) -> list[disnake.ui.Container]:
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    task = next((t for t in giveaway_data.get("tasks", []) if t["id"] == task_id), None)
    task_name = task.get("name", task_id) if task else task_id

    options = [
        disnake.SelectOption(label="Participação", value="reaction", description="Necessita que as pessoas cliquem em participar."),
        disnake.SelectOption(label="Global", value="global", description="Todos participam, mas só quem tem requisitos ganha."),
        disnake.SelectOption(label="Por Palavra", value="keyword", description="Quem falar a palavra-chave no canal ganha."),
    ]

    select = disnake.ui.StringSelect(
        placeholder="Selecione o modo de participação...",
        options=options,
        custom_id=f"GiveawayTask_SelectMode_{giveaway_id}_{task_id}"
    )

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > {giveaway_name} > Tarefa: {task_name} > **Definir Modo**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(select)
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToEditor_{giveaway_id}_{task_id}")
    )
    
    return [container, buttons]

def ModeSelectView_embed(inter: disnake.Interaction, giveaway_id: str, task_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    task = next((t for t in giveaway_data.get("tasks", []) if t["id"] == task_id), None)
    task_name = task.get("name", task_id) if task else task_id

    embed = disnake.Embed(
        title=f"Definir Modo: {task_name}",
        description="Selecione como os membros participarão do sorteio."
    )
    
    options = [
        disnake.SelectOption(label="Participação", value="reaction", description="Necessita que as pessoas cliquem em participar."),
        disnake.SelectOption(label="Global", value="global", description="Todos participam, mas só quem tem requisitos ganha."),
        disnake.SelectOption(label="Por Palavra", value="keyword", description="Quem falar a palavra-chave no canal ganha."),
    ]

    select = disnake.ui.StringSelect(
        placeholder="Selecione o modo de participação...",
        options=options,
        custom_id=f"GiveawayTask_SelectMode_{giveaway_id}_{task_id}"
    )

    components = [
        disnake.ui.ActionRow(select),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToEditor_{giveaway_id}_{task_id}")
        )
    ]

    return embed, components
