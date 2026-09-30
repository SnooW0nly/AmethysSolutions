import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils
from .container_utils import ContainerUtils

# --- Modals ---

class EditButtonModal(disnake.ui.Modal):
    def __init__(self, giveaway_id: str, data: dict):
        self.giveaway_id = giveaway_id
        self.data = data
        
        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        current_style_en = data.get("style", "green")
        current_style_pt = next((pt for pt, en in color_map_pt_to_en.items() if en == current_style_en), "verde")

        components = [
            disnake.ui.TextInput(label="Texto do Botão", custom_id="label", value=data.get("label"), max_length=30, required=True, placeholder="Participar"),
            disnake.ui.TextInput(label="Emoji do Botão (Opcional)", custom_id="emoji", value=data.get("emoji"), required=False, max_length=100, placeholder="🎉 ou <:nome:ID>"),
            disnake.ui.TextInput(label="Estilo (verde, cinza, vermelho, azul)", custom_id="style", value=current_style_pt, max_length=10, required=True, placeholder="Ex: verde"),
        ]
        super().__init__(title="Editar Botão de Participação", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id)
        if not giveaway:
            return

        if "button" not in giveaway:
            giveaway["button"] = {}

        option_emoji = inter.text_values["emoji"]
        if option_emoji:
            validation = utils.validate_emoji_for_components(option_emoji)
            if not validation["valid"]:
                error_msg = validation.get("error", "Emoji inválido")
                return await message.error(inter, f"O emoji fornecido não é válido para uso em componentes. {error_msg}\n\nUse um emoji unicode (ex: ✅) ou um emoji customizado no formato <:nome:id>.")
            # Converter para string apropriada
            if isinstance(validation["emoji"], disnake.PartialEmoji):
                option_emoji = str(validation["emoji"])
            else:
                option_emoji = validation["emoji"]

        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        style_pt = inter.text_values.get("style", "verde").lower()
        style_en = color_map_pt_to_en.get(style_pt, "green")
        
        giveaway["button"]["label"] = inter.text_values["label"]
        giveaway["button"]["emoji"] = option_emoji
        giveaway["button"]["style"] = style_en
        db.salvar("database/giveaways/giveaways_data.json", config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter, self.giveaway_id))
        else:
            embed, components = MessageEditView_embed(inter, self.giveaway_id)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditEmbedModal(disnake.ui.Modal):
    def __init__(self, giveaway_id: str, data: dict):
        self.giveaway_id = giveaway_id
        components = [
            disnake.ui.TextInput(label="Título", custom_id="title", value=data.get("title"), max_length=256, placeholder="🎉 Sorteio 🎉", required=True),
            disnake.ui.TextInput(label="Descrição", custom_id="description", value=data.get("description"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para participar!", required=False),
            disnake.ui.TextInput(label="URL da Imagem/Banner", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/banner.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Conteúdo: Embed", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id)
        if not giveaway: return

        if "embed" not in giveaway:
            giveaway["embed"] = {}

        new_data = inter.text_values.copy()
        
        for key in ["color", "image_url", "thumbnail_url", "description"]:
             if key in new_data and not new_data[key]:
                giveaway["embed"].pop(key, None)
                del new_data[key]

        giveaway["embed"].update(new_data)
        db.salvar("database/giveaways/giveaways_data.json", config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter, self.giveaway_id))
        else:
            embed, components = MessageEditView_embed(inter, self.giveaway_id)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditContentModal(disnake.ui.Modal):
    def __init__(self, giveaway_id: str, data: dict):
        self.giveaway_id = giveaway_id
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=2000, placeholder="Clique no botão abaixo para participar...", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
        ]
        super().__init__(title="Editar Conteúdo: Texto Simples", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id, {})
        if not giveaway: return

        if "content" not in giveaway:
            giveaway["content"] = {}

        new_data = inter.text_values.copy()
        for key in ["image_url", "content"]:
            if key in new_data and not new_data[key]:
                giveaway["content"].pop(key, None)
                del new_data[key]

        giveaway["content"].update(new_data)
        db.salvar("database/giveaways/giveaways_data.json", config)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter, self.giveaway_id))
        else:
            embed, components = MessageEditView_embed(inter, self.giveaway_id)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditContainerModal(disnake.ui.Modal):
    def __init__(self, giveaway_id: str, data: dict):
        self.giveaway_id = giveaway_id
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content"), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para participar...", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url"), required=False, placeholder="https://i.imgur.com/imagem.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url"), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color"), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Conteúdo: Container", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id, {})
        if not giveaway: return

        if "container" not in giveaway:
            giveaway["container"] = {}

        new_data = inter.text_values.copy()
        
        for key in ["color", "image_url", "thumbnail_url", "content"]:
            if key in new_data and not new_data[key]:
                giveaway["container"].pop(key, None)
                del new_data[key]

        giveaway["container"].update(new_data)
        db.salvar("database/giveaways/giveaways_data.json", config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter, self.giveaway_id))
        else:
            embed, components = MessageEditView_embed(inter, self.giveaway_id)
            await inter.response.edit_message(content=None, embed=embed, components=components)

# --- Views ---

def MessageEditView_components(inter: disnake.Interaction, giveaway_id: str) -> list:
    config = db.obter("database/giveaways/giveaways_data.json")
    giveaway_data = config.get(giveaway_id, {})
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    style = giveaway_data.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(giveaway_data.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(giveaway_data.get("embed", {}).get("title"))
    elif style == "content":
        content_data = giveaway_data.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(giveaway_data.get("container", {}).get("content"))
    
    preview_enabled = button_configured and content_configured

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if button_configured else emoji.wrong} **Botão:** {'`Configurado`' if button_configured else '`Não Configurado`'}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    main_container_children = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_data.get('name', 'N/A')} > **Configurar Mensagem**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id=f"GiveawayMsgEdit_CycleStyle_{giveaway_id}"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id=f"GiveawayMsgEdit_EditButton_{giveaway_id}"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"GiveawayMsgEdit_EditContent_{giveaway_id}"),
        ),
    ]

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(*main_container_children, **container_kwargs)
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}"),
        disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id=f"GiveawayMsgEdit_Preview_{giveaway_id}", disabled=not preview_enabled),
    )

    return [container, buttons]

def MessageEditView_embed(inter: disnake.Interaction, giveaway_id: str):
    config = db.obter("database/giveaways/giveaways_data.json")
    giveaway_data = config.get(giveaway_id, {})

    primary_color_hex = db.get_document("custom_colors").get("primary")
    style = giveaway_data.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(giveaway_data.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(giveaway_data.get("embed", {}).get("title"))
    elif style == "content":
        content_data = giveaway_data.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(giveaway_data.get("container", {}).get("content"))
    
    preview_enabled = button_configured and content_configured

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if button_configured else emoji.wrong} **Botão:** {'`Configurado`' if button_configured else '`Não Configurado`'}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurar Mensagem do Sorteio",
        description=status_text,
        **embed_kwargs
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id=f"GiveawayMsgEdit_CycleStyle_{giveaway_id}"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id=f"GiveawayMsgEdit_EditButton_{giveaway_id}"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"GiveawayMsgEdit_EditContent_{giveaway_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}"),
            disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id=f"GiveawayMsgEdit_Preview_{giveaway_id}", disabled=not preview_enabled),
        )
    ]

    return embed, components

async def show_panel(inter: disnake.Interaction, giveaway_id: str):
    mode = db.get_document("custom_mode").get("mode")

    if mode == "embed":
        embed, components = MessageEditView_embed(inter, giveaway_id)
        await inter.edit_original_message(content=None, embed=embed, components=components)
    else:
        components = MessageEditView_components(inter, giveaway_id)
        await inter.edit_original_message(content=None, embed=None, components=components)
