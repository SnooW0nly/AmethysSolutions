import disnake
from functions.utils import utils
from functions.database import database as db
from functions.message import message, embed_message
from emoji import is_emoji
from functions.emoji import emoji

# --- MODAL ---

class AddOptionModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.CommandInteraction, panel_id: str, from_edit: bool = False):
        self.inter = inter
        self.panel_id = panel_id
        self.from_edit = from_edit
        components = [
            disnake.ui.TextInput(
                label="Nome da Opção",
                placeholder="Ex: Suporte para Vendas",
                custom_id="option_name",
                max_length=50,
            ),
            disnake.ui.TextInput(
                label="Descrição da Opção",
                placeholder="Clique aqui para tirar dúvidas sobre vendas",
                custom_id="option_description",
                style=disnake.TextInputStyle.paragraph,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="Emoji (Opcional)",
                placeholder="Ex: 🛒",
                custom_id="option_emoji",
                max_length=100,
                required=False
            ),
        ]
        super().__init__(title="Adicionar Nova Opção", components=components, custom_id=f"add_option_modal_{self.panel_id}")

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

        if "options" not in panel:
            panel["options"] = []

        if len(panel["options"]) >= 25:
            return await message.error(inter, "Você atingiu o limite de 25 opções para este painel.")

        option_id = utils.gerar_id()
        new_option = {
            "id": option_id,
            "name": option_name,
            "description": option_description,
        }
        if option_emoji:
            new_option["emoji"] = option_emoji
        
        panel["options"].append(new_option)

        db.save_document("tickets_config", config)
        
        if self.from_edit:
            from .config_opcoes import config_options_components, config_options_embed
            if mode == "components":
                components = config_options_components(inter, self.panel_id)
                await inter.edit_original_message(components=components)
            else:
                embed, components = config_options_embed(inter, self.panel_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            if mode == "components":
                components = create_options_components(self.panel_id, panel["name"], panel["options"])
                await inter.edit_original_message(components=components)
            else:
                embed, components = create_options_embed(self.panel_id, panel["name"], panel["options"])
                await inter.edit_original_message(content=None, embed=embed, components=components)

# --- EMBED MODE ---

class CreateOptionsViewEmbed(disnake.ui.View):
    def __init__(self, panel_id: str, options: list):
        super().__init__(timeout=None)
        self.panel_id = panel_id
        
        self.add_item(disnake.ui.Button(
            label="Adicionar Opção",
            emoji=emoji.plus,
            style=disnake.ButtonStyle.success,
            custom_id=f"TicketCreateOption_Add_{panel_id}",
            disabled=len(options) >= 25
        ))

        self.add_item(disnake.ui.Button(
            label="Continuar",
            emoji=emoji.arrow,
            style=disnake.ButtonStyle.primary,
            custom_id=f"TicketCreateOption_Continue_{panel_id}",
            disabled=not options 
        ))

def create_options_embed(panel_id: str, panel_name: str, options: list):
    embed = disnake.Embed(
        title=f"Opções do Painel: {panel_name}",
        description="Adicione as opções para o seu painel de ticket. Você pode adicionar até 25 opções."
    )
    if not options:
        embed.description += "\n\nNenhuma opção foi adicionada ainda."
    else:
        for option in options:
            # Validar emoji antes de usar
            opt_emoji = option.get("emoji")
            emoji_display = ""
            if opt_emoji:
                try:
                    parsed_emoji = utils.safe_get_emoji(opt_emoji)
                    if parsed_emoji:
                        emoji_display = f"{str(parsed_emoji)} "
                except Exception:
                    pass  # Ignorar emoji inválido
            
            name = f"{emoji_display}{option['name']}"
            embed.add_field(
                name=name,
                value=option['description'],
                inline=False
            )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Adicionar Opção",
                emoji=emoji.plus,
                style=disnake.ButtonStyle.success,
                custom_id=f"TicketCreateOption_Add_{panel_id}",
                disabled=len(options) >= 25
            ),
            disnake.ui.Button(
                label="Continuar",
                emoji=emoji.arrow,
                style=disnake.ButtonStyle.primary,
                custom_id=f"TicketCreateOption_Continue_{panel_id}",
                disabled=not options 
            )
        )
    ]
    return embed, components

# --- COMPONENTS MODE ---

def create_options_components(panel_id: str, panel_name: str, options: list):
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Criar Painel > **{panel_name}**"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay("Adicione as opções para o seu painel de ticket. Você pode adicionar até 25 opções."),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small)
    ]

    if not options:
        components.append(disnake.ui.TextDisplay("Nenhuma opção foi adicionada ainda."))
    else:
        for option in options:
            # Validar emoji antes de usar
            opt_emoji = option.get("emoji")
            emoji_display = ""
            if opt_emoji:
                try:
                    parsed_emoji = utils.safe_get_emoji(opt_emoji)
                    if parsed_emoji:
                        emoji_display = f"{str(parsed_emoji)} "
                except Exception:
                    pass  # Ignorar emoji inválido
            
            display_text = f"{emoji_display}**{option['name']}**\n{option['description']}" if emoji_display else f"**{option['name']}**\n{option['description']}"
            components.append(disnake.ui.TextDisplay(display_text))

    container = disnake.ui.Container(
        *components,
        **container_kwargs
    )

    action_row = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Adicionar Opção",
            emoji=emoji.plus,
            style=disnake.ButtonStyle.success,
            custom_id=f"TicketCreateOption_Add_{panel_id}",
            disabled=len(options) >= 25
        ),
        disnake.ui.Button(
            label="Continuar",
            emoji=emoji.arrow,
            style=disnake.ButtonStyle.primary,
            custom_id=f"TicketCreateOption_Continue_{panel_id}",
            disabled=not options
        )
    )

    return [container, action_row]
