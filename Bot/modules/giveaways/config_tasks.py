import disnake
import datetime
from functions.database import database as db
from functions.emoji import emoji
from .config_giveaways import get_giveaways
from functions.utils import utils
from functions.message import message, embed_message

class CreateTaskModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.Interaction, giveaway_id: str):
        self.inter = inter
        self.giveaway_id = giveaway_id
        components = [
            disnake.ui.TextInput(
                label="Nome da Tarefa",
                placeholder="Ex: Sorteio Semanal #1",
                custom_id="task_name",
                max_length=50,
                required=True,
            ),
        ]
        super().__init__(title="Criar Nova Tarefa", components=components, custom_id=f"create_task_modal_{giveaway_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        task_name = inter.text_values["task_name"]

        config = db.obter("database/giveaways/giveaways_data.json")
        if self.giveaway_id not in config:
            await inter.followup.send("Sorteio não encontrado.", ephemeral=True)
            return

        if "tasks" not in config[self.giveaway_id]:
            config[self.giveaway_id]["tasks"] = []

        new_task_id = utils.gerar_id(6)
        new_task = {
            "id": new_task_id,
            "name": task_name,
            "status": "pending",
            "author_id": inter.author.id,
            "created_at": int(disnake.utils.utcnow().timestamp())
        }
        config[self.giveaway_id]["tasks"].append(new_task)
        db.salvar("database/giveaways/giveaways_data.json", config)

        from tasks.giveaways.logger_giveaways import log_giveaway_event
        await log_giveaway_event(
            bot=inter.bot,
            giveaway_id=self.giveaway_id,
            title="Sorteios - Tarefa Criada",
            lines=[
                f"{emoji.giveaway} **Sorteio:** {config[self.giveaway_id].get('name')}",
                f"{emoji.settings} **Nova Tarefa:** {task_name} (`{new_task_id}`)",
                f"{emoji.member} **Executor:** {inter.author.mention}"
            ]
        )

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await self.inter.edit_original_message(components=TaskEditorView_components(inter, self.giveaway_id, new_task_id))
        else:
            embed, components = TaskEditorView_embed(inter, self.giveaway_id, new_task_id)
            await self.inter.edit_original_message(content=None, embed=embed, components=components)

def get_tasks_data(giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    tasks = giveaway_data.get("tasks", [])

    running = len([t for t in tasks if t.get("status") == "running"])
    finished = len([t for t in tasks if t.get("status") == "finished"])
    error = len([t for t in tasks if t.get("status") == "error"])

    return {
        "running": running,
        "finished": finished,
        "error": error,
        "total": len(tasks)
    }

def ManageTasksView_components(inter: disnake.Interaction, giveaway_id: str) -> list:
    tasks_data = get_tasks_data(giveaway_id)
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")

    status_text = (
        f"{emoji.embed} **Tarefas criadas:** `{tasks_data['total']}`\n"
        f"{emoji.reload} **Tarefas em andamento:** `{tasks_data['running']}`\n"
        f"{emoji.double_check} **Tarefas finalizadas:** `{tasks_data['finished']}`\n"
        f"{emoji.wrong} **Tarefas com erro:** `{tasks_data['error']}`"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > {giveaway_name} > **Gerenciar Tarefas**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar nova Tarefa", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"GiveawayTask_Create_{giveaway_id}"),
            disnake.ui.Button(label="Gerenciar Tarefa", style=disnake.ButtonStyle.grey, emoji=emoji.settings, custom_id=f"GiveawayTask_Manage_{giveaway_id}", disabled=tasks_data["total"] == 0),
        ),
        **container_kwargs
    )

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}")
    )
    return [container, buttons]

def ManageTasksView_embed(inter: disnake.Interaction, giveaway_id: str):
    tasks_data = get_tasks_data(giveaway_id)
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")

    description = (
        f"{emoji.reload} **Tarefas Criadas:** `{tasks_data['total']}`\n"
        f"{emoji.reload} **Tarefas em andamento:** `{tasks_data['running']}`\n"
        f"{emoji.double_check} **Tarefas finalizadas:** `{tasks_data['finished']}`\n"
        f"{emoji.wrong} **Tarefas com erro:** `{tasks_data['error']}`"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Gerenciador de Tarefas: {giveaway_name}",
        description=description,
        **embed_kwargs
    )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar nova Tarefa", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"GiveawayTask_Create_{giveaway_id}"),
            disnake.ui.Button(label="Gerenciar Tarefa", style=disnake.ButtonStyle.grey, emoji=emoji.settings, custom_id=f"GiveawayTask_Manage_{giveaway_id}", disabled=tasks_data["total"] == 0),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}")
        )
    ]

    return embed, components

def SelectTaskView_components(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    tasks = giveaway_data.get("tasks", [])

    status_map = {
        "pending": f"Pendente",
        "running": f"Em andamento",
        "finished": f"Finalizada",
        "error": f"Com Erro"
    }
    options = [
        disnake.SelectOption(
            label=task.get('name', f"Tarefa ID: {task['id']}"),
            value=task['id'],
            emoji=emoji.clock if task.get('status', 'pending') == 'pending' else emoji.reload if task.get('status', 'pending') == 'running' else emoji.double_check if task.get('status', 'pending') == 'finished' else emoji.wrong,
            description=status_map.get(task.get('status', 'pending'))
        ) for task in tasks
    ]
    if not options:
        options.append(disnake.SelectOption(label="Nenhuma tarefa encontrada", value="disabled"))

    select = disnake.ui.StringSelect(
        placeholder="Selecione uma tarefa para gerenciar...",
        options=options,
        custom_id=f"GiveawayTask_SelectToManage_{giveaway_id}",
        disabled=not tasks
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > {giveaway_name} > **Selecionar Tarefa**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(select),
        **container_kwargs
    )

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToDashboard_{giveaway_id}")
    )

    return [container, buttons]

def SelectTaskView_embed(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    tasks = giveaway_data.get("tasks", [])

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Selecionar Tarefa: {giveaway_name}",
        description="Selecione uma das tarefas abaixo para editar suas configurações.",
        **embed_kwargs
    )

    status_map = {
        "pending": f"Pendente",
        "running": f"Em andamento",
        "finished": f"Finalizada",
        "error": f"Com Erro"
    }
    options = [
        disnake.SelectOption(
            label=task.get('name', f"Tarefa ID: {task['id']}"),
            value=task['id'],
            emoji=emoji.clock if task.get('status', 'pending') == 'pending' else emoji.reload if task.get('status', 'pending') == 'running' else emoji.double_check if task.get('status', 'pending') == 'finished' else emoji.wrong,
            description=status_map.get(task.get('status', 'pending'))
        ) for task in tasks
    ]
    if not options:
        options.append(disnake.SelectOption(label="Nenhuma tarefa encontrada", value="disabled"))

    select = disnake.ui.StringSelect(
        placeholder="Selecione uma tarefa para gerenciar...",
        options=options,
        custom_id=f"GiveawayTask_SelectToManage_{giveaway_id}",
        disabled=not tasks
    )

    components = [
        disnake.ui.ActionRow(select),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToDashboard_{giveaway_id}")
        )
    ]

    return embed, components


def RepostConfirmationView_components(giveaway_id: str, task_id: str):
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Repostar Sorteio"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(
            "Você está prestes a repostar um sorteio finalizado.\n"
            "Escolha como lidar com os vencedores da rodada anterior:"
        ),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Repostar (Limpando Vencedores)",
                style=disnake.ButtonStyle.danger,
                custom_id=f"GiveawayTask_ConfirmRepostClear_{giveaway_id}_{task_id}"
            ),
            disnake.ui.Button(
                label="Repostar (Mantendo Vencedores)",
                style=disnake.ButtonStyle.secondary,
                custom_id=f"GiveawayTask_ConfirmRepostKeep_{giveaway_id}_{task_id}"
            )
        ),
        **container_kwargs
    )
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToEditor_{giveaway_id}_{task_id}")
    )
    return [container, buttons]

def RepostConfirmationView_embed(giveaway_id: str, task_id: str):
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Repostar Sorteio",
        description="Escolha como lidar com os vencedores da rodada anterior:",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Repostar (Limpando Vencedores)",
                style=disnake.ButtonStyle.danger,
                custom_id=f"GiveawayTask_ConfirmRepostClear_{giveaway_id}_{task_id}"
            ),
            disnake.ui.Button(
                label="Repostar (Mantendo Vencedores)",
                style=disnake.ButtonStyle.secondary,
                custom_id=f"GiveawayTask_ConfirmRepostKeep_{giveaway_id}_{task_id}"
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToEditor_{giveaway_id}_{task_id}")
        )
    ]
    return embed, components

def TaskEditorView_components(inter: disnake.Interaction, giveaway_id: str, task_id: str) -> list[disnake.ui.Container]:
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    task = next((t for t in giveaway_data.get("tasks", []) if t["id"] == task_id), None)

    if not task:
        return ManageTasksView_components(inter, giveaway_id)

    task_name = task.get("name", task_id)
    message_id = task.get("message_id")
    status = task.get("status")

    channel_id = task.get("channel_id")
    channel = inter.bot.get_channel(channel_id) if channel_id else None

    style = giveaway_data.get("message_style", "embed")
    content_configured = False
    if style == "embed":
        content_configured = bool(giveaway_data.get("embed", {}).get("title"))
    elif style == "content":
        content_data = giveaway_data.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(giveaway_data.get("container", {}).get("content"))

    is_repostable = status in ["finished", "error"]
    send_button_label = "Enviar"
    send_button_action = "SendMessage"

    if is_repostable:
        send_button_label = "Repostar"
        send_button_action = "ResendMessage"
    elif message_id:
        send_button_label = "Reenviar"
        send_button_action = "ResendMessage"

    start_time = task.get("start_time")
    end_time = task.get("end_time")
    if start_time and end_time:
        start_dt = datetime.datetime.fromtimestamp(start_time)
        end_dt = datetime.datetime.fromtimestamp(end_time)
        duration_str = f"{start_dt.strftime('%d/%m/%Y %H:%M')} á {end_dt.strftime('%d/%m/%Y %H:%M')}"
    else:
        duration_str = "`Não definido`"

    min_participants = task.get("min_participants", "Não definido")
    max_participants = task.get("max_participants", "Não definido")
    participation_mode = task.get("participation_mode", "reaction")

    modes = {
        "reaction": "Participação",
        "global": "Global",
        "keyword": "Palavra-Chave"
    }
    mode_keys = list(modes.keys())
    current_mode_index = mode_keys.index(participation_mode)
    mode_label = f"Modo ({current_mode_index + 1}/{len(modes)})"


    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    status_text = (
        f"{emoji.receipt} **Canal do Sorteio:** {channel.mention if channel else '`Não Definido`'}\n"
        f"{emoji.route} **Modo de Participação:** `{modes.get(participation_mode, 'N/A')}`\n"
        f"{emoji.time} **Duração:** `{duration_str}`\n"
        f"{emoji.members} **Participantes (Mín/Máx):** `{min_participants}` / `{max_participants}`\n"
        f"{emoji.flag} **Ganhadores:** `{task.get('max_winners', 1)}`"
    )

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > {giveaway_name} > **Tarefa: {task_name}**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label=send_button_label,
                emoji=emoji.arrow,
                style=disnake.ButtonStyle.green,
                custom_id=f"GiveawayTask_{send_button_action}_{giveaway_id}_{task_id}",
                disabled=not channel_id or not content_configured
            ),
            disnake.ui.Button(label="Sortear Novamente", style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id=f"GiveawayTask_Reroll_{giveaway_id}_{task_id}", disabled=status != "finished"),
            disnake.ui.Button(label="Sortear", style=disnake.ButtonStyle.danger, emoji=emoji.flag, custom_id=f"GiveawayTask_Roll_{giveaway_id}_{task_id}", disabled=status != "running"),
        ),
       # disnake.ui.ActionRow(
            # disnake.ui.Button(label=mode_label, style=disnake.ButtonStyle.blurple, emoji=emoji.route, custom_id=f"GiveawayTask_CyclePartMode_{giveaway_id}_{task_id}"),
        #),
         disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id=f"GiveawayTask_SetChannel_{giveaway_id}_{task_id}"),
            disnake.ui.Button(label="Definir Duração", style=disnake.ButtonStyle.blurple, emoji=emoji.time, custom_id=f"GiveawayTask_SetDuration_{giveaway_id}_{task_id}"),
            disnake.ui.Button(label="Definir Participantes", style=disnake.ButtonStyle.blurple, emoji=emoji.members, custom_id=f"GiveawayTask_SetParticipants_{giveaway_id}_{task_id}"),
        ),
        **container_kwargs
    )

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToDashboard_{giveaway_id}"),
        disnake.ui.Button(label="Apagar Tarefa", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"GiveawayTask_Delete_{giveaway_id}_{task_id}")
    )

    return [container, buttons]

def TaskEditorView_embed(inter: disnake.Interaction, giveaway_id: str, task_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    task = next((t for t in giveaway_data.get("tasks", []) if t["id"] == task_id), None)

    if not task:
        return ManageTasksView_embed(inter, giveaway_id)

    task_name = task.get("name", task_id)
    message_id = task.get("message_id")
    status = task.get("status")

    channel_id = task.get("channel_id")
    channel = inter.bot.get_channel(channel_id) if channel_id else None

    style = giveaway_data.get("message_style", "embed")
    content_configured = False
    if style == "embed":
        content_configured = bool(giveaway_data.get("embed", {}).get("title"))
    elif style == "content":
        content_data = giveaway_data.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(giveaway_data.get("container", {}).get("content"))

    is_repostable = status in ["finished", "error"]
    send_button_label = "Enviar"
    send_button_action = "SendMessage"

    if is_repostable:
        send_button_label = "Repostar"
        send_button_action = "ResendMessage"
    elif message_id:
        send_button_label = "Reenviar"
        send_button_action = "ResendMessage"

    start_time = task.get("start_time")
    end_time = task.get("end_time")
    if start_time and end_time:
        start_dt = datetime.datetime.fromtimestamp(start_time)
        end_dt = datetime.datetime.fromtimestamp(end_time)
        duration_str = f"{start_dt.strftime('%d/%m/%Y %H:%M')} á {end_dt.strftime('%d/%m/%Y %H:%M')}"
    else:
        duration_str = "`Não definido`"

    min_participants = task.get("min_participants", "Não definido")
    max_participants = task.get("max_participants", "Não definido")
    participation_mode = task.get("participation_mode", "reaction")

    modes = {
        "reaction": "Participação",
        "global": "Global",
        "keyword": "Palavra-Chave"
    }
    mode_keys = list(modes.keys())
    current_mode_index = mode_keys.index(participation_mode)
    mode_label = f"Modo ({current_mode_index + 1}/{len(modes)})"

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(title=f"Editando Tarefa ({task_name}): {giveaway_name}", **embed_kwargs)

    status_text = (
        f"{emoji.textc} **Canal do Sorteio:** {channel.mention if channel else '`Não Definido`'}\n"
        f"{emoji.route} **Modo de Participação:** `{modes.get(participation_mode, 'N/A')}`\n"
        f"{emoji.time} **Duração:** `{duration_str}`\n"
        f"{emoji.members} **Participantes (Mín/Máx):** `{min_participants}` / `{max_participants}`\n"
        f"{emoji.flag} **Ganhadores:** `{task.get('max_winners', 1)}`"
    )
    embed.add_field(name="Configurações Atuais", value=status_text, inline=False)

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label=send_button_label,
                style=disnake.ButtonStyle.green,
                emoji=emoji.arrow,
                custom_id=f"GiveawayTask_{send_button_action}_{giveaway_id}_{task_id}",
                disabled=not channel_id or not content_configured
            ),
            disnake.ui.Button(label="Sortear Novamente", style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id=f"GiveawayTask_Reroll_{giveaway_id}_{task_id}", disabled=status != "finished"),
            disnake.ui.Button(label="Sortear", style=disnake.ButtonStyle.danger, emoji=emoji.flag, custom_id=f"GiveawayTask_Roll_{giveaway_id}_{task_id}", disabled=status != "running"),
        ),
       # disnake.ui.ActionRow(
            # disnake.ui.Button(label=mode_label, style=disnake.ButtonStyle.blurple, emoji=emoji.route, custom_id=f"GiveawayTask_CyclePartMode_{giveaway_id}_{task_id}"),
        #),
         disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id=f"GiveawayTask_SetChannel_{giveaway_id}_{task_id}"),
            disnake.ui.Button(label="Definir Duração", style=disnake.ButtonStyle.blurple, emoji=emoji.time, custom_id=f"GiveawayTask_SetDuration_{giveaway_id}_{task_id}"),
            disnake.ui.Button(label="Definir Participantes", style=disnake.ButtonStyle.blurple, emoji=emoji.members, custom_id=f"GiveawayTask_SetParticipants_{giveaway_id}_{task_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayTask_BackToDashboard_{giveaway_id}"),
            disnake.ui.Button(label="Apagar Tarefa", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"GiveawayTask_Delete_{giveaway_id}_{task_id}")
        )
    ]

    return embed, components