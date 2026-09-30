import disnake
from disnake import *
import math

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
import core

class edit_status:
    class add_status_modal(disnake.ui.Modal):
        def __init__(self):
            components = [
                disnake.ui.TextInput(
                    label="Nome do Status",
                    placeholder="Digite o nome do status",
                    custom_id="nome_status",
                    style=TextInputStyle.short,
                    required=True,
                    max_length=100,
                ),
            ]
            super().__init__(title="Adicionar Novo Status", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            mode = db.get_document("custom_mode").get("mode")
            nome = inter.text_values.get("nome_status")
            
            database = db.get_document("custom_status")
            tasks = database.get("tasks", [])
            
            if not tasks and "names" in database:
                old_type = database.get("type", "online")
                tasks = [{"type": old_type, "activity": "custom", "name": n} for n in database.get("names", [])]
            
            tasks.append({"type": "online", "activity": "custom", "name": nome})
            database["tasks"] = tasks
            
            if "names" in database: del database["names"]
            if "name" in database: del database["name"]
            if "type" in database: del database["type"]

            db.save_document("custom_status", {}, database)
            await core.change_status(inter.bot)
            
            if mode == "embed":
                embed, components = edit_status.get_main_panel_embed(inter)
                await inter.response.edit_message(content=None, embed=embed, components=components)
            else:
                await inter.response.edit_message(components=edit_status.get_main_panel_components(inter))

    class edit_task_name_modal(disnake.ui.Modal):
        def __init__(self, task_idx: int, current_name: str):
            self.task_idx = task_idx
            components = [
                disnake.ui.TextInput(
                    label="Novo Nome do Status",
                    placeholder="Digite o novo nome",
                    custom_id="nome_status",
                    value=current_name,
                    style=TextInputStyle.short,
                    required=True,
                    max_length=100,
                ),
            ]
            super().__init__(title="Editar Nome do Status", components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            mode = db.get_document("custom_mode").get("mode")
            nome = inter.text_values.get("nome_status")
            
            database = db.get_document("custom_status")
            tasks = database.get("tasks", [])
            
            if 0 <= self.task_idx < len(tasks):
                tasks[self.task_idx]["name"] = nome
                database["tasks"] = tasks
                db.save_document("custom_status", {}, database)
                await core.change_status(inter.bot)
            
            if mode == "embed":
                embed, components = edit_status.get_task_panel_embed(inter, self.task_idx)
                await inter.response.edit_message(content=None, embed=embed, components=components)
            else:
                await inter.response.edit_message(components=edit_status.get_task_panel_components(inter, self.task_idx))

    @staticmethod
    def get_tasks_from_db():
        database = db.get_document("custom_status")
        tasks = database.get("tasks", [])
        if not tasks and "names" in database:
            old_type = database.get("type", "online")
            tasks = [{"type": old_type, "activity": "custom", "name": n} for n in database.get("names", [])]
        return tasks

    @staticmethod
    async def delete_task(idx: int, bot):
        database = db.get_document("custom_status")
        tasks = database.get("tasks", [])
        if 0 <= idx < len(tasks):
            tasks.pop(idx)
            database["tasks"] = tasks
            db.save_document("custom_status", {}, database)
            await core.change_status(bot)
            
    @staticmethod
    async def change_task_type(idx: int, new_type: str, bot):
        database = db.get_document("custom_status")
        tasks = database.get("tasks", [])
        if 0 <= idx < len(tasks):
            tasks[idx]["type"] = new_type
            database["tasks"] = tasks
            db.save_document("custom_status", {}, database)
            await core.change_status(bot)

    @staticmethod
    async def change_task_activity(idx: int, new_activity: str, bot):
        database = db.get_document("custom_status")
        tasks = database.get("tasks", [])
        if 0 <= idx < len(tasks):
            tasks[idx]["activity"] = new_activity
            database["tasks"] = tasks
            db.save_document("custom_status", {}, database)
            await core.change_status(bot)

    @staticmethod
    def get_main_panel_components(inter: disnake.MessageInteraction, page: int = 0):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        tasks = edit_status.get_tasks_from_db()
        total_tasks = len(tasks)
        max_per_page = 100
        total_pages = max(1, math.ceil(total_tasks / max_per_page))
        page = max(0, min(page, total_pages - 1))

        start_idx = page * max_per_page
        end_idx = min(start_idx + max_per_page, total_tasks)
        page_tasks = tasks[start_idx:end_idx]

        statusemoji = {
            "online":  emoji.online,
            "idle":    emoji.idle,
            "dnd":     emoji.dnd,
            "streaming": emoji.streaming,
            "offline": emoji.off,
        }
        activityemoji = {
            "custom":    "💬",
            "playing":   "🎮",
            "listening": "🎵",
            "watching":  "📺",
            "streaming": "📡",
            "competing": "🏆",
        }

        comps = []
        comps.append(disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Personalização > **Status**"))
        comps.append(disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small))
        comps.append(disnake.ui.TextDisplay(f"Gerencie as Tasks do status que o bot irá rotacionar.\n**Total de status cadastrados:** `{total_tasks}`"))
        comps.append(disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small))

        if not page_tasks:
            comps.append(disnake.ui.TextDisplay("Nenhum status configurado. Clique em **Adicionar Status** para criar."))
        else:
            chunks = [page_tasks[i:i + 25] for i in range(0, len(page_tasks), 25)]
            for chunk_idx, chunk in enumerate(chunks):
                options = []
                for i, task in enumerate(chunk):
                    global_idx = start_idx + (chunk_idx * 25) + i
                    label = task["name"][:100]
                    act = task.get("activity", "custom")
                    act_icon = activityemoji.get(act, "💬")
                    options.append(disnake.SelectOption(
                        label=label,
                        description=f"Presença: {task['type']} · Atividade: {act_icon} {act}",
                        value=str(global_idx),
                        emoji=statusemoji.get(task["type"], emoji.online)
                    ))
                comps.append(disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder=f"Selecione um status para gerenciar ({chunk_idx + 1}/{len(chunks)})",
                        custom_id=f"TaskSelect_{chunk_idx}",
                        options=options
                    )
                ))

        if total_pages > 1:
            comps.append(disnake.ui.ActionRow(
                disnake.ui.Button(label="◀ Anterior", style=disnake.ButtonStyle.grey, custom_id=f"StatusPage_{page - 1}", disabled=page == 0),
                disnake.ui.Button(label=f"Página {page + 1}/{total_pages}", style=disnake.ButtonStyle.grey, custom_id="StatusPage_Display", disabled=True),
                disnake.ui.Button(label="Próxima ▶", style=disnake.ButtonStyle.grey, custom_id=f"StatusPage_{page + 1}", disabled=page == total_pages - 1),
            ))

        main_container = disnake.ui.Container(*comps, **container_kwargs)

        nav_row = disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar Status", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Personalizacao_AddStatus"),
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Personalizacao"),
        )
        return [main_container, nav_row]

    @staticmethod
    def get_main_panel_embed(inter: disnake.MessageInteraction, page: int = 0):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(title="Editar Status Rotativo")
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        tasks = edit_status.get_tasks_from_db()
        total_tasks = len(tasks)
        max_per_page = 100
        total_pages = max(1, math.ceil(total_tasks / max_per_page))
        page = max(0, min(page, total_pages - 1))

        start_idx = page * max_per_page
        end_idx = min(start_idx + max_per_page, total_tasks)
        page_tasks = tasks[start_idx:end_idx]

        embed.description = f"Gerencie as Tasks do status que o bot irá rotacionar.\n**Total de status cadastrados:** `{total_tasks}`"

        statusemoji = {
            "online":    emoji.online,
            "idle":      emoji.idle,
            "dnd":       emoji.dnd,
            "streaming": emoji.streaming,
            "offline":   emoji.off,
        }
        activityemoji = {
            "custom":    "💬",
            "playing":   "🎮",
            "listening": "🎵",
            "watching":  "📺",
            "streaming": "📡",
            "competing": "🏆",
        }

        components = []
        if not page_tasks:
            embed.description += "\n\nNenhum status configurado. Clique em **Adicionar Status** para criar."
        else:
            chunks = [page_tasks[i:i + 25] for i in range(0, len(page_tasks), 25)]
            for chunk_idx, chunk in enumerate(chunks):
                options = []
                for i, task in enumerate(chunk):
                    global_idx = start_idx + (chunk_idx * 25) + i
                    label = task["name"][:100]
                    act = task.get("activity", "custom")
                    act_icon = activityemoji.get(act, "💬")
                    options.append(disnake.SelectOption(
                        label=label,
                        description=f"Presença: {task['type']} · Atividade: {act_icon} {act}",
                        value=str(global_idx),
                        emoji=statusemoji.get(task["type"], emoji.online)
                    ))
                components.append(disnake.ui.ActionRow(
                    disnake.ui.StringSelect(placeholder=f"Selecione um status ({chunk_idx + 1}/{len(chunks)})", custom_id=f"TaskSelect_{chunk_idx}", options=options)
                ))

        if total_pages > 1:
            components.append(disnake.ui.ActionRow(
                disnake.ui.Button(label="◀ Anterior", style=disnake.ButtonStyle.grey, custom_id=f"StatusPage_{page - 1}", disabled=page == 0),
                disnake.ui.Button(label=f"Página {page + 1}/{total_pages}", style=disnake.ButtonStyle.grey, custom_id="StatusPage_Display", disabled=True),
                disnake.ui.Button(label="Próxima ▶", style=disnake.ButtonStyle.grey, custom_id=f"StatusPage_{page + 1}", disabled=page == total_pages - 1),
            ))

        components.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar Status", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Personalizacao_AddStatus"),
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Personalizacao"),
        ))
        return embed, components

    @staticmethod
    def get_task_panel_components(inter: disnake.MessageInteraction, task_idx: int):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex: container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        tasks = edit_status.get_tasks_from_db()
        if not (0 <= task_idx < len(tasks)): return edit_status.get_main_panel_components(inter)
        task = tasks[task_idx]

        statusname = {
            "online":  "Online",
            "idle":    "Ausente",
            "dnd":     "Não Perturbar",
            "offline": "Invisível",
        }
        statusemoji = {
            "online":  emoji.online,
            "idle":    emoji.idle,
            "dnd":     emoji.dnd,
            "offline": emoji.off,
        }
        activityname = {
            "custom":    "Mensagem Personalizada",
            "playing":   "Jogando",
            "listening": "Ouvindo",
            "watching":  "Assistindo",
            "streaming": "Transmitindo",
            "competing": "Competindo em",
        }
        activityemoji_map = {
            "custom":    "💬",
            "playing":   "🎮",
            "listening": "🎵",
            "watching":  "📺",
            "streaming": "📡",
            "competing": "🏆",
        }

        current_presence = task.get("type", "online")
        current_activity = task.get("activity", "custom")

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Personalização > Status > **Gerenciar Task**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"**Detalhes do Status #{task_idx + 1}:**\n"
                    f"-# Nome: `{task['name']}`\n"
                    f"-# Presença: {statusemoji.get(current_presence, '')} `{statusname.get(current_presence, current_presence)}`\n"
                    f"-# Atividade: {activityemoji_map.get(current_activity, '💬')} `{activityname.get(current_activity, current_activity)}`"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Alterar Presença (bolinha colorida)",
                        custom_id=f"TaskEditType_{task_idx}",
                        options=[
                            disnake.SelectOption(label="Online",         value="online",  emoji=emoji.online,  default=current_presence == "online"),
                            disnake.SelectOption(label="Ausente",        value="idle",    emoji=emoji.idle,    default=current_presence == "idle"),
                            disnake.SelectOption(label="Não Perturbar",  value="dnd",     emoji=emoji.dnd,     default=current_presence == "dnd"),
                            disnake.SelectOption(label="Invisível",      value="offline", emoji=emoji.off,     default=current_presence == "offline"),
                        ]
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Alterar Tipo de Atividade (texto exibido)",
                        custom_id=f"TaskEditActivity_{task_idx}",
                        options=[
                            disnake.SelectOption(label="Mensagem Personalizada", value="custom",    emoji="💬", description="Exibe o texto livremente", default=current_activity == "custom"),
                            disnake.SelectOption(label="Jogando",                value="playing",   emoji="🎮", description='Prefixo "Jogando"',        default=current_activity == "playing"),
                            disnake.SelectOption(label="Ouvindo",                value="listening", emoji="🎵", description='Prefixo "Ouvindo"',         default=current_activity == "listening"),
                            disnake.SelectOption(label="Assistindo",             value="watching",  emoji="📺", description='Prefixo "Assistindo"',      default=current_activity == "watching"),
                            disnake.SelectOption(label="Transmitindo",           value="streaming", emoji="📡", description='Prefixo "Transmitindo" + URL Twitch', default=current_activity == "streaming"),
                            disnake.SelectOption(label="Competindo em",          value="competing", emoji="🏆", description='Prefixo "Competindo em"',   default=current_activity == "competing"),
                        ]
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Editar Nome", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"TaskEditName_{task_idx}"),
                    disnake.ui.Button(label="Deletar Status", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"TaskDel_{task_idx}"),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar aos Status", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="TaskBack"))
        ]

    @staticmethod
    def get_task_panel_embed(inter: disnake.MessageInteraction, task_idx: int):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        tasks = edit_status.get_tasks_from_db()
        if not (0 <= task_idx < len(tasks)): return edit_status.get_main_panel_embed(inter)
        task = tasks[task_idx]

        embed = disnake.Embed(title=f"Gerenciar Status #{task_idx + 1}")
        if primary_color_hex: embed.color = int(primary_color_hex.replace("#", ""), 16)

        statusname = {
            "online":  "Online",
            "idle":    "Ausente",
            "dnd":     "Não Perturbar",
            "offline": "Invisível",
        }
        statusemoji = {
            "online":  emoji.online,
            "idle":    emoji.idle,
            "dnd":     emoji.dnd,
            "offline": emoji.off,
        }
        activityname = {
            "custom":    "Mensagem Personalizada",
            "playing":   "Jogando",
            "listening": "Ouvindo",
            "watching":  "Assistindo",
            "streaming": "Transmitindo",
            "competing": "Competindo em",
        }
        activityemoji_map = {
            "custom":    "💬",
            "playing":   "🎮",
            "listening": "🎵",
            "watching":  "📺",
            "streaming": "📡",
            "competing": "🏆",
        }

        current_presence = task.get("type", "online")
        current_activity = task.get("activity", "custom")

        embed.description = (
            f"**Detalhes do Status:**\n"
            f"-# Nome: `{task['name']}`\n"
            f"-# Presença: {statusemoji.get(current_presence, '')} `{statusname.get(current_presence, current_presence)}`\n"
            f"-# Atividade: {activityemoji_map.get(current_activity, '💬')} `{activityname.get(current_activity, current_activity)}`"
        )

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Alterar Presença (bolinha colorida)",
                    custom_id=f"TaskEditType_{task_idx}",
                    options=[
                        disnake.SelectOption(label="Online",        value="online",  emoji=emoji.online, default=current_presence == "online"),
                        disnake.SelectOption(label="Ausente",       value="idle",    emoji=emoji.idle,   default=current_presence == "idle"),
                        disnake.SelectOption(label="Não Perturbar", value="dnd",     emoji=emoji.dnd,    default=current_presence == "dnd"),
                        disnake.SelectOption(label="Invisível",     value="offline", emoji=emoji.off,    default=current_presence == "offline"),
                    ]
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Alterar Tipo de Atividade (texto exibido)",
                    custom_id=f"TaskEditActivity_{task_idx}",
                    options=[
                        disnake.SelectOption(label="Mensagem Personalizada", value="custom",    emoji="💬", description='Exibe o texto livremente',              default=current_activity == "custom"),
                        disnake.SelectOption(label="Jogando",                value="playing",   emoji="🎮", description='Prefixo "Jogando"',                     default=current_activity == "playing"),
                        disnake.SelectOption(label="Ouvindo",                value="listening", emoji="🎵", description='Prefixo "Ouvindo"',                      default=current_activity == "listening"),
                        disnake.SelectOption(label="Assistindo",             value="watching",  emoji="📺", description='Prefixo "Assistindo"',                   default=current_activity == "watching"),
                        disnake.SelectOption(label="Transmitindo",           value="streaming", emoji="📡", description='Prefixo "Transmitindo" + URL Twitch',    default=current_activity == "streaming"),
                        disnake.SelectOption(label="Competindo em",          value="competing", emoji="🏆", description='Prefixo "Competindo em"',                default=current_activity == "competing"),
                    ]
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Nome", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"TaskEditName_{task_idx}"),
                disnake.ui.Button(label="Deletar Status", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"TaskDel_{task_idx}"),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar aos Status", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="TaskBack"))
        ]
        return embed, components