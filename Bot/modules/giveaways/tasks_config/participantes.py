import disnake
from functions.database import database as db
from functions.emoji import emoji
from ..config_giveaways import get_giveaways

class LimitsModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.Interaction, giveaway_id: str, task_id: str, task_data: dict):
        self.inter = inter
        self.giveaway_id = giveaway_id
        self.task_id = task_id
        
        components = [
            disnake.ui.TextInput(
                label="Mínimo de Participantes",
                custom_id="min_participants",
                value=str(task_data.get("min_participants", "0")),
                placeholder="Ex: 10",
                min_length=1,
                max_length=5,
                required=False
            ),
            disnake.ui.TextInput(
                label="Máximo de Participantes",
                custom_id="max_participants",
                value=str(task_data.get("max_participants", "0")),
                placeholder="0 para ilimitado. Ex: 100",
                min_length=1,
                max_length=5,
                required=False
            ),
            disnake.ui.TextInput(
                label="Número de Ganhadores",
                custom_id="max_winners",
                value=str(task_data.get("max_winners", "1")),
                placeholder="Ex: 1",
                min_length=1,
                max_length=2,
                required=True
            ),
        ]
        super().__init__(title="Definir Limites e Ganhadores", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id, {})
        task = next((t for t in giveaway.get("tasks", []) if t.get("id") == self.task_id), None)
        if not task:
            await inter.response.send_message(f"{emoji.wrong} Erro: Tarefa não encontrada.", ephemeral=True)
            return

        min_participants = inter.text_values["min_participants"]
        max_participants = inter.text_values["max_participants"]
        max_winners = inter.text_values["max_winners"]

        try:
            task["min_participants"] = int(min_participants) if min_participants else 0
            task["max_participants"] = int(max_participants) if max_participants else 0
            task["max_winners"] = int(max_winners) if max_winners else 1
        except ValueError:
            await inter.response.send_message(f"{emoji.wrong} Por favor, insira apenas números válidos.", ephemeral=True)
            return

        db.salvar("database/giveaways/giveaways_data.json", config)
        
        from tasks.giveaways.logger_giveaways import log_giveaway_event
        await log_giveaway_event(
            bot=inter.bot,
            giveaway_id=self.giveaway_id,
            title="Sorteios - Configuração de Tarefa Alterada",
            lines=[
                f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                f"{emoji.settings} **Tarefa:** {task.get('name')}",
                f"{emoji.edit} **Limites Atualizados:** Mín: `{task['min_participants']}`, Máx: `{task['max_participants']}`, Ganhadores: `{task['max_winners']}`",
                f"{emoji.member} **Executor:** {inter.author.mention}"
            ]
        )
        
        await inter.response.send_message(f"{emoji.correct} Configurações salvas com sucesso!", ephemeral=True)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            components = await ParticipantsConfigView_components(self.inter, self.giveaway_id, self.task_id)
            await self.inter.edit_original_message(components=components)
        else:
            embed, components = await ParticipantsConfigView_embed(self.inter, self.giveaway_id, self.task_id)
            await self.inter.edit_original_message(content=None, embed=embed, components=components)


async def ParticipantsConfigView_components(inter: disnake.Interaction, giveaway_id: str, task_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    task = next((t for t in giveaway_data.get("tasks", []) if t.get("id") == task_id), {})
    
    participants_count = len(task.get("participants", []))

    min_participants = task.get("min_participants", "Não definido")
    max_participants = task.get("max_participants", "Não definido")
    if max_participants == 0: max_participants = "Ilimitado"
    max_winners = task.get("max_winners", "1")

    status_text = (
        f"{emoji.members} **Participantes Atuais:** `{participants_count}`\n"
        f"{emoji.members} **Mínimo de Participantes:** `{min_participants}`\n"
        f"{emoji.members} **Máximo de Participantes:** `{max_participants}`\n"
        f"{emoji.flag} **Número de Ganhadores:** `{max_winners}`"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > **Configurar Participantes**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Limites/Ganhadores", style=disnake.ButtonStyle.blurple, emoji=emoji.arrow, custom_id=f"GiveawayParticipants_SetLimits_{giveaway_id}_{task_id}"),
        ),
        **container_kwargs
    )

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayParticipants_Back_{giveaway_id}_{task_id}"),
        disnake.ui.Button(
            label="Limpar Participantes",
            style=disnake.ButtonStyle.danger,
            emoji=emoji.delete,
            custom_id=f"GiveawayParticipants_Clear_{giveaway_id}_{task_id}",
            disabled=not participants_count
        )
    )

    return [container, buttons]

async def ParticipantsConfigView_embed(inter: disnake.Interaction, giveaway_id: str, task_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    task = next((t for t in giveaway_data.get("tasks", []) if t.get("id") == task_id), {})
    
    participants_count = len(task.get("participants", []))

    min_participants = task.get("min_participants", "Não definido")
    max_participants = task.get("max_participants", "Não definido")
    if max_participants == 0: max_participants = "Ilimitado"
    max_winners = task.get("max_winners", "1")

    description = (
        f"{emoji.members} **Participantes Atuais:** `{participants_count}`\n"
        f"{emoji.members} **Mínimo de Participantes:** `{min_participants}`\n"
        f"{emoji.members} **Máximo de Participantes:** `{max_participants}`\n"
        f"{emoji.flag} **Número de Ganhadores:** `{max_winners}`"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurando Participantes: {giveaway_name}",
        description=description,
        **embed_kwargs
    )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Limites/Ganhadores", style=disnake.ButtonStyle.blurple, emoji=emoji.arrow, custom_id=f"GiveawayParticipants_SetLimits_{giveaway_id}_{task_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayParticipants_Back_{giveaway_id}_{task_id}"),
            disnake.ui.Button(
                label="Limpar Participantes",
                style=disnake.ButtonStyle.danger,
                emoji=emoji.delete,
                custom_id=f"GiveawayParticipants_Clear_{giveaway_id}_{task_id}",
                disabled=not participants_count
            )
        )
    ]

    return embed, components
