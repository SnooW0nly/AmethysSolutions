import disnake
from functions.database import database as db
from functions.emoji import emoji

class QuestionModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.CommandInteraction, panel_id: str, option_id: str, question_id: str = None):
        self.inter = inter
        self.panel_id = panel_id
        self.option_id = option_id
        self.question_id = question_id

        config = db.get_document("tickets_config") or {}
        form_data = config.get("panels", {}).get(panel_id, {}).get("forms", {}).get(option_id, [])
        question_data = next((q for q in form_data if str(q.get("id")) == question_id), None) if question_id else None

        title = "Editar Pergunta" if question_data else "Adicionar Pergunta"
        
        components = [
            disnake.ui.TextInput(
                label="Rótulo da Pergunta",
                placeholder="Ex: Qual é o seu problema?",
                custom_id="question_label",
                max_length=45,
                value=question_data.get("label", "") if question_data else ""
            ),
            disnake.ui.TextInput(
                label="Placeholder (Opcional)",
                placeholder="Ex: Descreva seu problema em detalhes.",
                custom_id="question_placeholder",
                max_length=100,
                value=question_data.get("placeholder", "") if question_data else "",
                required=False
            ),
            disnake.ui.TextInput(
                label="Estilo (short/paragraph)",
                placeholder="short ou paragraph",
                custom_id="question_style",
                max_length=9,
                value="paragraph" if (question_data and question_data.get("style") == "paragraph") else "short"
            ),
            disnake.ui.TextInput(
                label="Obrigatório (Sim/Não)",
                placeholder="Sim ou Não",
                custom_id="question_required",
                max_length=3,
                value="sim" if (question_data and question_data.get("required")) else "nao"
            ),
        ]
        super().__init__(title=title, components=components, custom_id=f"question_modal_{self.panel_id}_{self.option_id}_{self.question_id or ''}")

    async def callback(self, inter: disnake.ModalInteraction):
        # A lógica será tratada no cog
        pass

class SelectFormOption(disnake.ui.StringSelect):
    def __init__(self, panel_id: str, options: list):
        select_options = [
            disnake.SelectOption(
                label=opt['name'],
                value=str(opt['id']),
                description=opt.get('description', '')[:100],
                emoji=opt.get('emoji') or None
            ) for opt in options
        ]
        is_disabled = not options
        if not options:
            select_options.append(disnake.SelectOption(label="Nenhuma opção para configurar formulário", value="placeholder"))

        super().__init__(
            placeholder="Selecione uma opção para aplicar o formulário...",
            options=select_options,
            custom_id=f"TicketForm_SelectOption_{panel_id}",
            disabled=is_disabled
        )

def config_form_select_components(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    options = panel_data.get("options", [])
    panel_name = panel_data.get("name", "N/A")
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container_components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > {panel_name} > Preferências > **Formulários**"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay("Selecione a opção de ticket à qual o formulário será aplicado.\nSe não houver opções, crie uma primeiro."),
        disnake.ui.ActionRow(SelectFormOption(panel_id, options)),
    ]

    container = disnake.ui.Container(*container_components, **container_kwargs)
    back_button_row = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}")
    )
    
    return [container, back_button_row]

def config_form_select_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    options = panel_data.get("options", [])
    panel_name = panel_data.get("name", "N/A")
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurar Formulários: {panel_name}",
        description="Selecione a opção de ticket à qual o formulário será aplicado. Se não houver opções, crie uma primeiro.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(SelectFormOption(panel_id, options)),
        disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketPref_Back_{panel_id}"))
    ]

    return embed, components

class SelectQuestionToEdit(disnake.ui.StringSelect):
    def __init__(self, panel_id: str, option_id: str, questions: list):
        select_options = [
            disnake.SelectOption(
                label=q['label'],
                value=str(q['id']),
                description=f"Obrigatório: {'Sim' if q.get('required') else 'Não'}"
            ) for q in questions
        ]
        
        is_disabled = not questions
        if not questions:
            select_options.append(disnake.SelectOption(label="Nenhuma pergunta para editar", value="placeholder"))

        super().__init__(
            placeholder="Selecione uma pergunta para editar...",
            options=select_options,
            custom_id=f"TicketForm_SelectToEdit_{panel_id}_{option_id}",
            disabled=is_disabled
        )

class SelectQuestionToRemove(disnake.ui.StringSelect):
    def __init__(self, panel_id: str, option_id: str, questions: list):
        select_options = [
            disnake.SelectOption(
                label=q['label'],
                value=str(q['id']),
            ) for q in questions
        ]
        
        is_disabled = not questions
        if not questions:
            select_options.append(disnake.SelectOption(label="Nenhuma pergunta para remover", value="placeholder"))

        super().__init__(
            placeholder="Selecione uma ou mais perguntas para remover...",
            options=select_options,
            custom_id=f"TicketForm_SelectToRemove_{panel_id}_{option_id}",
            min_values=1,
            max_values=len(questions) if questions else 1,
            disabled=is_disabled
        )

def config_form_editor_components(inter: disnake.Interaction, panel_id: str, option_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get("name", "N/A")
    
    option_data = next((opt for opt in panel_data.get("options", []) if str(opt.get("id")) == option_id), None)
    option_name = option_data.get("name", "N/A") if option_data else "Opção não encontrada"

    questions = panel_data.get("forms", {}).get(option_id, [])
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Preferências > Formulários > **{option_name}**"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"Gerencie as perguntas do formulário. Atualmente há **{len(questions)}/5** perguntas."),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
    ]

    if questions:
        components.extend([
            disnake.ui.ActionRow(SelectQuestionToEdit(panel_id, option_id, questions)),
            disnake.ui.ActionRow(SelectQuestionToRemove(panel_id, option_id, questions)),
        ])
    else:
        components.append(disnake.ui.TextDisplay("Nenhuma pergunta configurada para esta opção."))

    options = panel_data.get("options", [])

    back_button_id = f"TicketForm_BackToSelect_{panel_id}"
    if len(options) <= 1:
        back_button_id = f"TicketPref_Back_{panel_id}"
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=back_button_id),
        disnake.ui.Button(label="Adicionar Pergunta", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id=f"TicketForm_Add_{panel_id}_{option_id}", disabled=len(questions) >= 5),
    )
    
    container = disnake.ui.Container(*components, **container_kwargs)
    
    return [container, buttons]

def config_form_editor_embed(inter: disnake.Interaction, panel_id: str, option_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    panel_name = panel_data.get("name", "N/A")

    option_data = next((opt for opt in panel_data.get("options", []) if str(opt.get("id")) == option_id), None)
    option_name = option_data.get("name", "N/A") if option_data else "Opção não encontrada"

    questions = panel_data.get("forms", {}).get(option_id, [])
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editando Formulário: {option_name}",
        description=f"Gerencie as perguntas do formulário. Você tem **{len(questions)}/5** perguntas.",
        **embed_kwargs
    )

    components = []
    if not questions:
        embed.description = "Nenhuma pergunta configurada para esta opção."
    else:
        for q in questions:
            embed.add_field(
                name=f"{q['label']} ({'Obrigatório' if q.get('required') else 'Opcional'})",
                value=f"Estilo: {q.get('style', 'short')}",
                inline=False
            )
        
        components.extend([
            disnake.ui.ActionRow(SelectQuestionToEdit(panel_id, option_id, questions)),
            disnake.ui.ActionRow(SelectQuestionToRemove(panel_id, option_id, questions)),
        ])
    
    options = panel_data.get("options", [])

    back_button_id = f"TicketForm_BackToSelect_{panel_id}"
    if len(options) <= 1:
        back_button_id = f"TicketPref_Back_{panel_id}"

    action_buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=back_button_id),
        disnake.ui.Button(label="Adicionar Pergunta", style=disnake.ButtonStyle.success, emoji=emoji.plus, custom_id=f"TicketForm_Add_{panel_id}_{option_id}", disabled=len(questions) >= 5),
    )
    components.append(action_buttons)
    
    return embed, components
