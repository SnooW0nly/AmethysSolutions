import disnake
from functions.database import database as db
from functions.emoji import emoji

def get_option_data(panel_id: str, option_id: str) -> dict:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    options = panel_data.get("options", [])
    return next((opt for opt in options if str(opt.get("id")) == option_id), {})

def config_form_select_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    options = panel_data.get("options", [])
    
    select_options = [
        disnake.SelectOption(
            label=opt.get("name", f"ID: {opt.get('id')}"),
            value=str(opt.get("id")),
            emoji=opt.get("emoji") or None
        ) for opt in options
    ]

    select = disnake.ui.StringSelect(
        custom_id=f"TicketForm_SelectOption_{panel_id}",
        placeholder="Selecione uma opção para configurar o formulário",
        options=select_options
    )
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Preferências > Formulários > **Selecionar Opção**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(select),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
    )
    
    return [container, buttons]

def config_form_select_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get('name', 'N/A')
    options = panel_data.get("options", [])

    select_options = [
        disnake.SelectOption(
            label=opt.get("name", f"ID: {opt.get('id')}"),
            value=str(opt.get("id")),
            emoji=opt.get("emoji") or None
        ) for opt in options
    ]

    select = disnake.ui.StringSelect(
        custom_id=f"TicketForm_SelectOption_{panel_id}",
        placeholder="Selecione uma opção para configurar",
        options=select_options
    )
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurar Formulário: {panel_name}",
        description="Este painel possui múltiplas opções de ticket. Selecione a opção para a qual deseja configurar um formulário.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(select),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
        )
    ]
    return embed, components


def config_form_editor_components(inter: disnake.Interaction, panel_id: str, option_id: str) -> list:
    option_data = get_option_data(panel_id, option_id)
    option_name = option_data.get('name', 'N/A')
    questions = option_data.get("form", [])

    header = f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Preferências > Formulários > **{option_name}**"
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    components = [
        disnake.ui.TextDisplay(header),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]

    if questions:
        question_list = "\n".join([f"- `{q['label']}`" for q in questions])
        components.append(disnake.ui.TextDisplay(f"**Perguntas Atuais:**\n{question_list}"))
        
        edit_select = disnake.ui.StringSelect(
            custom_id=f"TicketForm_SelectToEdit_{panel_id}_{option_id}",
            placeholder="Selecione uma pergunta para editar...",
            options=[disnake.SelectOption(label=q['label'], value=str(q['id'])) for q in questions]
        )
        remove_select = disnake.ui.StringSelect(
            custom_id=f"TicketForm_SelectToRemove_{panel_id}_{option_id}",
            placeholder="Selecione perguntas para remover...",
            min_values=1,
            max_values=len(questions),
            options=[disnake.SelectOption(label=q['label'], value=str(q['id'])) for q in questions]
        )
        components.extend([
            disnake.ui.ActionRow(edit_select),
            disnake.ui.ActionRow(remove_select)
        ])
    else:
        components.append(disnake.ui.TextDisplay("Nenhuma pergunta configurada para esta opção."))

    container = disnake.ui.Container(*components, **container_kwargs)
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketForm_BackToSelect_{panel_id}"),
        disnake.ui.Button(label="Adicionar Pergunta", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"TicketForm_Add_{panel_id}_{option_id}"),
    )
    
    return [container, buttons]

def config_form_editor_embed(inter: disnake.Interaction, panel_id: str, option_id: str):
    option_data = get_option_data(panel_id, option_id)
    option_name = option_data.get('name', 'N/A')
    questions = option_data.get("form", [])
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
    
    embed = disnake.Embed(
        title=f"Editando Formulário: {option_name}",
        **embed_kwargs
    )
    
    components = []
    if questions:
        question_list = "\n".join([f"**{i+1}.** {q['label']}" for i, q in enumerate(questions)])
        embed.description = f"**Perguntas Atuais:**\n{question_list}"
        
        edit_select = disnake.ui.StringSelect(
            custom_id=f"TicketForm_SelectToEdit_{panel_id}_{option_id}",
            placeholder="Selecione uma pergunta para editar...",
            options=[disnake.SelectOption(label=q['label'], value=str(q['id'])) for q in questions]
        )
        remove_select = disnake.ui.StringSelect(
            custom_id=f"TicketForm_SelectToRemove_{panel_id}_{option_id}",
            placeholder="Selecione perguntas para remover...",
            min_values=1,
            max_values=len(questions),
            options=[disnake.SelectOption(label=q['label'], value=str(q['id'])) for q in questions]
        )
        components.extend([
            disnake.ui.ActionRow(edit_select),
            disnake.ui.ActionRow(remove_select)
        ])
    else:
        embed.description = "Nenhuma pergunta configurada para esta opção."

    action_buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketForm_BackToSelect_{panel_id}"),
        disnake.ui.Button(label="Adicionar Pergunta", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"TicketForm_Add_{panel_id}_{option_id}"),
    )
    components.append(action_buttons)
    
    return embed, components
