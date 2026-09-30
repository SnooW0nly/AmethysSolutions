import disnake
from functions.utils import utils
from functions.database import database as db
from functions.message import message, embed_message
from emoji import is_emoji
from functions.emoji import emoji

# --- MODAL ---

class EditOptionModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.CommandInteraction, panel_id: str, option_id: str):
        self.inter = inter
        self.panel_id = panel_id
        self.option_id = option_id

        config = db.get_document("tickets_config") or {}
        panel = config.get("panels", {}).get(panel_id, {})
        option_data = next((opt for opt in panel.get("options", []) if str(opt.get("id")) == option_id), None)

        if not option_data:
            option_data = {"name": "", "description": "", "emoji": ""}

        components = [
            disnake.ui.TextInput(
                label="Nome da Opção",
                placeholder="Ex: Suporte para Vendas",
                custom_id="option_name",
                max_length=50,
                value=option_data.get("name", "")
            ),
            disnake.ui.TextInput(
                label="Descrição da Opção",
                placeholder="Clique aqui para tirar dúvidas sobre vendas",
                custom_id="option_description",
                style=disnake.TextInputStyle.paragraph,
                max_length=100,
                value=option_data.get("description", "")
            ),
            disnake.ui.TextInput(
                label="Emoji (Opcional)",
                placeholder="Ex: 🛒",
                custom_id="option_emoji",
                max_length=100,
                value=option_data.get("emoji", ""),
                required=False
            ),
        ]
        super().__init__(title="Editar Opção", components=components, custom_id=f"edit_option_modal_{self.panel_id}_{self.option_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        option_name = inter.text_values["option_name"]
        option_description = inter.text_values["option_description"]
        option_emoji = inter.text_values["option_emoji"]
        
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
        
        config = db.get_document("tickets_config") or {}
        panel = config["panels"][self.panel_id]
        
        option_found = False
        for option in panel.get("options", []):
            if str(option.get("id")) == self.option_id:
                option["name"] = option_name
                option["description"] = option_description
                if option_emoji:
                    option["emoji"] = option_emoji
                elif "emoji" in option:
                    del option["emoji"]
                option_found = True
                break
        
        if not option_found:
            return await message.error(inter, "A opção que você tentou editar não foi encontrada.")

        db.save_document("tickets_config", config)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            components = config_options_components(inter, self.panel_id)
            await inter.edit_original_message(components=components)
        else:
            embed, components = config_options_embed(inter, self.panel_id)
            await inter.edit_original_message(content=None, embed=embed, components=components)

# --- VIEWS ---

class SelectOptionToEdit(disnake.ui.StringSelect):
    def __init__(self, panel_id: str, options: list):
        select_options = []
        for opt in options:
            try:
                # Validar emoji de forma segura
                opt_emoji = opt.get('emoji')
                parsed_emoji = None
                if opt_emoji:
                    parsed_emoji = utils.safe_get_emoji(opt_emoji)
                
                select_options.append(
                    disnake.SelectOption(
                        label=opt['name'], 
                        value=str(opt['id']),
                        description=opt.get('description', '')[:100],
                        emoji=parsed_emoji
                    )
                )
            except Exception:
                # Se houver erro, criar sem emoji
                select_options.append(
                    disnake.SelectOption(
                        label=opt['name'], 
                        value=str(opt['id']),
                        description=opt.get('description', '')[:100],
                        emoji=None
                    )
                )
        
        is_disabled = not options
        if not options:
            select_options.append(disnake.SelectOption(label="Nenhuma opção para editar", value="placeholder"))

        super().__init__(
            placeholder="Selecione uma opção para editar...",
            options=select_options,
            custom_id=f"TicketOptions_SelectToEdit_{panel_id}",
            disabled=is_disabled
        )

class SelectOptionToRemove(disnake.ui.StringSelect):
    def __init__(self, panel_id: str, options: list):
        select_options = []
        for opt in options:
            try:
                # Validar emoji de forma segura
                opt_emoji = opt.get('emoji')
                parsed_emoji = None
                if opt_emoji:
                    parsed_emoji = utils.safe_get_emoji(opt_emoji)
                
                select_options.append(
                    disnake.SelectOption(
                        label=opt['name'], 
                        value=str(opt['id']),
                        description=f"Clique para remover esta opção",
                        emoji=parsed_emoji
                    )
                )
            except Exception:
                # Se houver erro, criar sem emoji
                select_options.append(
                    disnake.SelectOption(
                        label=opt['name'], 
                        value=str(opt['id']),
                        description=f"Clique para remover esta opção",
                        emoji=None
                    )
                )
        
        is_disabled = not options
        if not options:
            select_options.append(disnake.SelectOption(label="Nenhuma opção para remover", value="placeholder"))

        super().__init__(
            placeholder="Selecione uma ou mais opções para remover...",
            options=select_options,
            custom_id=f"TicketOptions_SelectToRemove_{panel_id}",
            min_values=1,
            max_values=len(options) if options else 1,
            disabled=is_disabled
        )

# --- COMPONENTS MODE ---

def config_options_components(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id)
    if not panel_data:
        return []

    panel_name = panel_data.get("name", "N/A")
    options = panel_data.get("options", [])
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container_components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > **{panel_name}** > **Editar Opções**"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(f"Gerencie as opções do painel. Atualmente há **{len(options)}/25** opções."),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Adicionar Opção",
                emoji=emoji.plus,
                style=disnake.ButtonStyle.success,
                custom_id=f"TicketOptions_Add_{panel_id}",
                disabled=len(options) >= 25
            )
        ),
        disnake.ui.ActionRow(SelectOptionToEdit(panel_id, options)),
        disnake.ui.ActionRow(SelectOptionToRemove(panel_id, options)),
    ]

    container = disnake.ui.Container(
        *container_components,
        **container_kwargs
    )

    back_button_row = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id=f"TicketEdit_BackToPanel_{panel_id}"
        )
    )
    
    return [container, back_button_row]

# --- EMBED MODE ---

class ConfigOptionsViewEmbed(disnake.ui.View):
    def __init__(self, inter: disnake.Interaction, panel_id: str):
        super().__init__(timeout=None)
        
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id, {})
        options = panel_data.get("options", [])

        self.add_item(SelectOptionToEdit(panel_id, options))
        self.add_item(SelectOptionToRemove(panel_id, options))

        self.add_item(disnake.ui.Button(
            label="Adicionar Opção",
            emoji=emoji.plus,
            style=disnake.ButtonStyle.success,
            custom_id=f"TicketOptions_Add_{panel_id}",
            disabled=len(options) >= 25,
            row=2
        ))
        
        self.add_item(disnake.ui.Button(
            label="Voltar",
            style=disnake.ButtonStyle.grey,
            emoji=emoji.back,
            custom_id=f"TicketEdit_BackToPanel_{panel_id}",
            row=2
        ))


def config_options_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id)
    if not panel_data:
        return None, None 

    panel_name = panel_data.get("name", "N/A")
    options = panel_data.get("options", [])
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editando Opções: {panel_name}",
        description=f"Gerencie as opções do painel. Você tem **{len(options)}/25** opções.",
        **embed_kwargs
    )
    
    if not options:
        embed.description += "\n\nNenhuma opção foi adicionada ainda."
    else:
        for option in options:
            # Validar emoji antes de usar
            opt_emoji = option.get('emoji')
            emoji_display = ""
            if opt_emoji:
                try:
                    parsed_emoji = utils.safe_get_emoji(opt_emoji)
                    if parsed_emoji:
                        emoji_display = f"{str(parsed_emoji)} "
                except Exception:
                    pass  # Ignorar emoji inválido
            
            embed.add_field(
                name=f"{emoji_display}{option['name']}",
                value=option['description'],
                inline=False
            )
    
    components = [
        disnake.ui.ActionRow(SelectOptionToEdit(panel_id, options)),
        disnake.ui.ActionRow(SelectOptionToRemove(panel_id, options)),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Adicionar Opção",
                emoji=emoji.plus,
                style=disnake.ButtonStyle.success,
                custom_id=f"TicketOptions_Add_{panel_id}",
                disabled=len(options) >= 25
            ),
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id=f"TicketEdit_BackToPanel_{panel_id}"
            )
        )
    ]
        
    return embed, components
