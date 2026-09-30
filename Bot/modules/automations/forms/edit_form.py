import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from . import helpers

def get_forms():
    config = helpers.carregar_config()
    return config.get("forms", {})

class SelectFormToEdit(disnake.ui.StringSelect):
    def __init__(self, forms_chunk: list[tuple[str, dict]], chunk_index: int, total_forms: int):
        options = [
            disnake.SelectOption(label=data["name"], value=form_id, description=f"Clique para editar o formulário")
            for form_id, data in forms_chunk
        ]

        placeholder = "Selecione um formulário para editar..."
        if total_forms > 25:
            start_index = chunk_index * 25 + 1
            end_index = start_index + len(forms_chunk) - 1
            placeholder = f"Selecione um formulário... ({start_index}-{end_index})"

        if not options and total_forms == 0:
            options.append(disnake.SelectOption(label="Nenhum formulário encontrado", value="disabled"))

        super().__init__(
            placeholder=placeholder,
            options=options,
            custom_id=f"select_form_to_edit_{chunk_index}",
            disabled=(total_forms == 0)
        )

def EditFormView_components() -> list[disnake.ui.Container]:
    forms = get_forms()
    form_items = list(forms.items())
    num_forms = len(form_items)
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > Formulários > **Editar Formulário**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small)
    ]

    if num_forms == 0:
        select = SelectFormToEdit([], 0, 0)
        container_components.append(disnake.ui.ActionRow(select))
    else:
        chunk_size = 25
        for i in range(0, num_forms, chunk_size):
            chunk_index = i // chunk_size
            chunk = form_items[i:i + chunk_size]
            select = SelectFormToEdit(chunk, chunk_index, num_forms)
            container_components.append(disnake.ui.ActionRow(select))
            
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(*container_components, **container_kwargs)
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Forms_Painel"),
    )
    
    return [container, buttons]

def EditFormView_embed():
    forms = get_forms()
    form_items = list(forms.items())
    num_forms = len(form_items)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editar Formulário",
        description="Selecione um formulário abaixo para editar suas configurações.",
        **embed_kwargs
    )

    components = []
    if num_forms == 0:
        select = SelectFormToEdit([], 0, 0)
        components.append(disnake.ui.ActionRow(select))
    else:
        chunk_size = 25
        for i in range(0, num_forms, chunk_size):
            chunk_index = i // chunk_size
            chunk = form_items[i:i + chunk_size]
            select = SelectFormToEdit(chunk, chunk_index, num_forms)
            components.append(disnake.ui.ActionRow(select))

    components.append(disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Forms_Painel"),
    ))

    return embed, components

def SpecificFormView_components(form_id: str) -> list[disnake.ui.Container]:
    forms = get_forms()
    form_data = forms.get(form_id)
    if not form_data:
        return EditFormView_components()

    form_name = form_data.get('name', 'N/A')
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > Formulários > Editando > **{form_name}**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id=f"FormEdit_SetMessage_{form_id}"),
            disnake.ui.Button(label="Definir Perguntas", style=disnake.ButtonStyle.grey, emoji=emoji.question, custom_id=f"FormEdit_SetQuestions_{form_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Configurações Gerais", style=disnake.ButtonStyle.grey, emoji=emoji.settings2, custom_id=f"FormEdit_Advanced_{form_id}"),
            disnake.ui.Button(label="Estatísticas Gerais", style=disnake.ButtonStyle.grey, emoji=emoji.chart, custom_id=f"FormEdit_Stats_{form_id}"),
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Forms_Editar"),
    )
    
    return [container, buttons]

def SpecificFormView_embed(form_id: str):
    forms = get_forms()
    form_data = forms.get(form_id)
    if not form_data:
        return EditFormView_embed()

    form_name = form_data.get('name', 'N/A')
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editando Formulário > {form_name}",
        description="Selecione uma das opções abaixo para configurar o formulário.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id=f"FormEdit_SetMessage_{form_id}"),
            disnake.ui.Button(label="Definir Perguntas", style=disnake.ButtonStyle.grey, emoji=emoji.question, custom_id=f"FormEdit_SetQuestions_{form_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Configurações Gerais", style=disnake.ButtonStyle.grey, emoji=emoji.settings2, custom_id=f"FormEdit_Advanced_{form_id}"),
            disnake.ui.Button(label="Estatísticas Gerais", style=disnake.ButtonStyle.grey, emoji=emoji.chart, custom_id=f"FormEdit_Stats_{form_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Forms_Editar"),
        )
    ]

    return embed, components
