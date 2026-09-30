import disnake
from functions.database import database as db
from functions.emoji import emoji
from .task_manager import get_tasks_data, get_all_tasks, get_task
from .auth_counter import get_auth_count

async def ManageTasksView_components(inter: disnake.Interaction) -> list:
    tasks_data = get_tasks_data()
    auth_count = await get_auth_count()

    status_text = (
        f"{emoji.reload} **Tasks em andamento:** `{tasks_data['running']}`\n"
        f"{emoji.double_check} **Tasks finalizadas:** `{tasks_data['finished']}`\n"
        f"{emoji.wrong} **Tasks com erro:** `{tasks_data['error']}`\n"
    )

    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Gerenciar Tarefas**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar nova Task", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="CloudTasks_Create"),
            disnake.ui.Button(label="Gerenciar Task", style=disnake.ButtonStyle.grey, emoji=emoji.settings, custom_id="CloudTasks_Manage"),
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_Back")
    )
    return [container, buttons]

def ManageTasksView_embed(inter: disnake.Interaction):
    tasks_data = get_tasks_data()

    description = (
        f"{emoji.reload} **Tasks em andamento:** `{tasks_data['running']}`\n"
        f"{emoji.double_check} **Tasks finalizadas:** `{tasks_data['finished']}`\n"
        f"{emoji.wrong} **Tasks com erro:** `{tasks_data['error']}`"
    )
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Gerenciador de Tarefas",
        description=description,
        **embed_kwargs
    )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar nova Task", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="CloudTasks_Create"),
            disnake.ui.Button(label="Gerenciar Task", style=disnake.ButtonStyle.grey, emoji=emoji.settings, custom_id="CloudTasks_Manage"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Cloud_Back")
        )
    ]
    
    return embed, components

def ManageTasksSelectView_components(inter: disnake.Interaction) -> list:
    """Container com select menu para escolher uma task"""
    tasks = get_all_tasks()
    
    if not tasks:
        custom_colors = db.get_document("custom_colors") or {}
        primary_color_hex = custom_colors.get("primary", "#5c5ef0")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Gerenciar Tarefas**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay("Nenhuma task encontrada."),
            **container_kwargs
        )
        
        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudTasks_Back")
        )
        return [container, buttons]
    
    # Criar opções do select menu
    options = []
    for task in tasks[:25]:  # Limitar a 25 opções (limite do Discord)
        from datetime import datetime
        created_at = datetime.fromisoformat(task.get("created_at", ""))
        date_str = created_at.strftime("%d/%m/%Y às %H:%M")
        
        # Emoji baseado no tipo da task (igual ao modal)
        task_type = task.get("type", "")
        task_emoji = {
            "recover_members": emoji.reload,
            "verify_members": emoji.double_check,
            "send_dms": emoji.mail2,
            "list_members": emoji.embed
        }.get(task_type, emoji.reload)
        
        options.append(disnake.SelectOption(
            label=task.get('name', 'Task desconhecida'),
            value=task.get("id", ""),
            description=date_str,
            emoji=task_emoji
        ))
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
    
    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Gerenciar Tarefas**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        #disnake.ui.TextDisplay("Selecione uma task para ver os detalhes:"),
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder="Escolha uma task...",
                options=options,
                custom_id="CloudTasks_Select"
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudTasks_Back")
    )
    return [container, buttons]

def ManageTasksSelectView_embed(inter: disnake.Interaction):
    """Embed com select menu para escolher uma task"""
    tasks = get_all_tasks()
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    if not tasks:
        embed = disnake.Embed(
            title="Gerenciar Tarefas",
            description="Nenhuma task encontrada.",
            **embed_kwargs
        )
        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudTasks_Back")
        )
        return embed, [buttons]

    # Criar opções do select menu
    options = []
    for task in tasks[:25]:  # Limitar a 25 opções (limite do Discord)
        from datetime import datetime
        created_at = datetime.fromisoformat(task.get("created_at", ""))
        date_str = created_at.strftime("%d/%m/%Y às %H:%M")
        
        task_type = task.get("type", "")
        task_emoji = {
            "recover_members": emoji.reload,
            "verify_members": emoji.double_check,
            "send_dms": emoji.mail2,
            "list_members": emoji.embed
        }.get(task_type, emoji.reload)
        
        options.append(disnake.SelectOption(
            label=task.get('name', 'Task desconhecida'),
            value=task.get("id", ""),
            description=date_str,
            emoji=task_emoji
        ))

    embed = disnake.Embed(
        title="Gerenciar Tarefas",
        description="Selecione uma task para ver os detalhes:",
        **embed_kwargs
    )

    select_menu = disnake.ui.StringSelect(
        placeholder="Escolha uma task...",
        options=options,
        custom_id="CloudTasks_Select"
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudTasks_Back")
    )
    
    return embed, [disnake.ui.ActionRow(select_menu), buttons]

def TaskDetailsView_components(inter: disnake.Interaction, task_id: str) -> list:
    """Container com detalhes de uma task específica"""
    task = get_task(task_id)
    
    if not task:
        custom_colors = db.get_document("custom_colors") or {}
        primary_color_hex = custom_colors.get("primary", "#7289da")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Detalhes da Task**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay("Task não encontrada."),
            **container_kwargs
        )
        
        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudTasks_Back")
        )
        return [container, buttons]
    
    # Emoji baseado no status
    status_emoji = {
        "running": emoji.reload,
        "finished": emoji.double_check,
        "error": emoji.wrong
    }.get(task.get("status", "running"), emoji.reload)
    
    # Informações da task
    from datetime import datetime
    try:
        created_at = datetime.fromisoformat(task.get("created_at", ""))
        updated_at = datetime.fromisoformat(task.get("updated_at", ""))
    except (ValueError, TypeError) as e:
        print(f"Erro ao converter data da task {task_id}: {e}")
        # Usar data atual como fallback
        created_at = datetime.now()
        updated_at = datetime.now()
    
    details_text = f"""**Tipo de task:** {task.get('name', 'N/A')}
**Criado por:** {task.get('created_by', {}).get('name', 'N/A')}
**Criado em:** {created_at.strftime('%d/%m/%Y às %H:%M')}
**Atualizado em:** {updated_at.strftime('%d/%m/%Y às %H:%M')}"""
    
    # Adicionar informações específicas baseadas no tipo e dados
    task_data = task.get("data", {})
    if task.get("type") == "list_members":
        members_count = task_data.get("members_count", 0)
        details_text += f"\n**Total de membros listados:** `{members_count}`"
        
        if task_data.get("message"):
            details_text += f"\n**Mensagem:** {task_data.get('message')}"
    
    elif task.get("type") == "verify_members":
        verified_count = task_data.get("verified_count", 0)
        unverified_count = task_data.get("unverified_count", 0)
        total_members = task_data.get("total_members", 0)
        
        details_text += f"\n**Total de membros verificados:** `{total_members}`"
        details_text += f"\n**Membros verificados:** `{verified_count}`"
        details_text += f"\n**Membros desverificados:** `{unverified_count}`"
        
        # if task_data.get("message"):
        #     details_text += f"\n**Mensagem:** {task_data.get('message')}"
    
    elif task.get("type") == "recover_members":
        recovered_count = task_data.get("recovered_count", 0)
        failed_count = task_data.get("failed_count", 0)
        total_verified = task_data.get("total_verified", 0)
        
        details_text += f"\n**Total de verificados:** `{total_verified}`"
        details_text += f"\n**Membros recuperados:** `{recovered_count}`"
        details_text += f"\n**Falhas na recuperação:** `{failed_count}`"
        
        if task_data.get("message"):
            details_text += f"\n**Mensagem:** {task_data.get('message')}"
    
    # if task_data.get("error"):
    #     details_text += f"\n**Erro:** {task_data.get('error')}"
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
    
    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > AmyCloud > **Detalhes da Task**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(details_text),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudTasks_Back")
    )
    return [container, buttons]

def TaskDetailsView_embed(inter: disnake.Interaction, task_id: str):
    """Embed com detalhes de uma task específica"""
    task = get_task(task_id)
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    if not task:
        embed = disnake.Embed(
            title="Detalhes da Task",
            description="Task não encontrada.",
            **embed_kwargs
        )
        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudTasks_Back")
        )
        return embed, [buttons]

    # Emoji baseado no status
    status_emoji = {
        "running": emoji.reload,
        "finished": emoji.double_check,
        "error": emoji.wrong
    }.get(task.get("status", "running"), emoji.reload)
    
    # Informações da task
    from datetime import datetime
    try:
        created_at = datetime.fromisoformat(task.get("created_at", ""))
        updated_at = datetime.fromisoformat(task.get("updated_at", ""))
    except (ValueError, TypeError) as e:
        print(f"Erro ao converter data da task {task_id}: {e}")
        created_at = datetime.now()
        updated_at = datetime.now()
    
    details_text = f"""**Tipo de task:** {task.get('name', 'N/A')}
**Criado por:** {task.get('created_by', {}).get('name', 'N/A')}
**Criado em:** {created_at.strftime('%d/%m/%Y às %H:%M')}
**Atualizado em:** {updated_at.strftime('%d/%m/%Y às %H:%M')}"""
    
    # Adicionar informações específicas baseadas no tipo e dados
    task_data = task.get("data", {})
    if task.get("type") == "list_members":
        members_count = task_data.get("members_count", 0)
        details_text += f"\n**Total de membros listados:** `{members_count}`"
        
        if task_data.get("message"):
            details_text += f"\n**Mensagem:** {task_data.get('message')}"
    
    elif task.get("type") == "verify_members":
        verified_count = task_data.get("verified_count", 0)
        unverified_count = task_data.get("unverified_count", 0)
        total_members = task_data.get("total_members", 0)
        
        details_text += f"\n**Total de membros verificados:** `{total_members}`"
        details_text += f"\n**Membros verificados:** `{verified_count}`"
        details_text += f"\n**Membros desverificados:** `{unverified_count}`"
        
    elif task.get("type") == "recover_members":
        recovered_count = task_data.get("recovered_count", 0)
        failed_count = task_data.get("failed_count", 0)
        total_verified = task_data.get("total_verified", 0)
        
        details_text += f"\n**Total de verificados:** `{total_verified}`"
        details_text += f"\n**Membros recuperados:** `{recovered_count}`"
        details_text += f"\n**Falhas na recuperação:** `{failed_count}`"
        
        if task_data.get("message"):
            details_text += f"\n**Mensagem:** {task_data.get('message')}"

    embed = disnake.Embed(
        title=f"{status_emoji} Detalhes da Task: {task.get('name', 'Task')}",
        description=details_text,
        **embed_kwargs
    )

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="CloudTasks_Back")
    )
    
    return embed, [buttons]
