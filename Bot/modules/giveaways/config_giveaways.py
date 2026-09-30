import disnake
from functions.utils import utils
from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji

def SelectModeView_components():
    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > **Criar Sorteio**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay("Primeiro, selecione o tipo de sorteio que você deseja criar."),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Sorteio Real", style=disnake.ButtonStyle.green, emoji=emoji.gift, custom_id="GiveawayCreate_SetMode_real"),
            disnake.ui.Button(label="Sorteio Falso", style=disnake.ButtonStyle.danger, emoji=emoji.gift2, custom_id="GiveawayCreate_SetMode_falso"),
        ),
    )
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Giveaways_Painel")
    )
    return [container, buttons]

def SelectModeView_embed():
    embed = disnake.Embed(
        title="Criar Sorteio",
        description="Primeiro, selecione o tipo de sorteio que você deseja criar."
    )
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Sorteio Real", style=disnake.ButtonStyle.green, emoji=emoji.gift, custom_id="GiveawayCreate_SetMode_real"),
            disnake.ui.Button(label="Sorteio Falso", style=disnake.ButtonStyle.danger, emoji=emoji.gift2, custom_id="GiveawayCreate_SetMode_falso"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Giveaways_Painel")
        )
    ]
    return embed, components

class CreateGiveawayModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.CommandInteraction, mode: str):
        self.inter = inter
        self.mode = mode
        components = [
            disnake.ui.TextInput(
                label="Nome do Sorteio",
                placeholder="Ex: Sorteio de Nitro",
                custom_id="giveaway_name",
                max_length=50,
            ),
        ]
        super().__init__(title="Criar Novo Sorteio", components=components, custom_id="create_giveaway_modal")

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        giveaway_id = utils.gerar_id()
        giveaway_name = inter.text_values["giveaway_name"]

        config = db.obter("database/giveaways/giveaways_data.json")
        if not config:
            config = {}
            
        config[giveaway_id] = {
            "name": giveaway_name,
            "mode": self.mode,
            "author_id": inter.author.id,
            "created_at": int(disnake.utils.utcnow().timestamp())
        }
        db.salvar("database/giveaways/giveaways_data.json", config)
        
        mode = db.get_document("custom_mode").get("mode")

        if mode == "components":
            components = SpecificGiveawayView_components(inter, giveaway_id)
            await inter.edit_original_message(components=components)
        else:
            embed, components = SpecificGiveawayView_embed(inter, giveaway_id)
            await inter.edit_original_message(content=None, embed=embed, components=components)

def get_giveaways():
    return db.obter("database/giveaways/giveaways_data.json") or {}

class SelectGiveawayToEdit(disnake.ui.StringSelect):
    def __init__(self, giveaways_chunk: list[tuple[str, dict]], chunk_index: int, total_giveaways: int):
        options = [
            disnake.SelectOption(label=data["name"], value=giveaway_id, description=f"Clique para editar o sorteio")
            for giveaway_id, data in giveaways_chunk
        ]

        placeholder = "Selecione um sorteio para editar..."
        if total_giveaways > 25:
            start_index = chunk_index * 25 + 1
            end_index = start_index + len(giveaways_chunk) - 1
            placeholder = f"Selecione um sorteio... ({start_index}-{end_index})"

        if not options and total_giveaways == 0:
            options.append(disnake.SelectOption(label="Nenhum sorteio encontrado", value="disabled"))

        super().__init__(
            placeholder=placeholder,
            options=options,
            custom_id=f"select_giveaway_to_edit_{chunk_index}",
            disabled=(total_giveaways == 0)
        )

def EditGiveawayView_components() -> list[disnake.ui.Container]:
    giveaways = get_giveaways()
    giveaway_items = list(giveaways.items())
    num_giveaways = len(giveaway_items)
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_components = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > **Editar Sorteio**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small)
    ]

    if num_giveaways == 0:
        select = SelectGiveawayToEdit([], 0, 0)
        container_components.append(disnake.ui.ActionRow(select))
    else:
        chunk_size = 25
        for i in range(0, num_giveaways, chunk_size):
            chunk_index = i // chunk_size
            chunk = giveaway_items[i:i + chunk_size]
            select = SelectGiveawayToEdit(chunk, chunk_index, num_giveaways)
            container_components.append(disnake.ui.ActionRow(select))
            
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(*container_components, **container_kwargs)
    
    buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Giveaways_Painel"),
        )
    
    return [container, buttons]

def EditGiveawayView_embed(inter: disnake.Interaction):
    giveaways = get_giveaways()
    giveaway_items = list(giveaways.items())
    num_giveaways = len(giveaway_items)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Editar Sorteio",
        description="Selecione um sorteio abaixo para editar suas configurações.",
        **embed_kwargs
    )

    components = []
    if num_giveaways == 0:
        select = SelectGiveawayToEdit([], 0, 0)
        components.append(disnake.ui.ActionRow(select))
    else:
        chunk_size = 25
        for i in range(0, num_giveaways, chunk_size):
            chunk_index = i // chunk_size
            chunk = giveaway_items[i:i + chunk_size]
            select = SelectGiveawayToEdit(chunk, chunk_index, num_giveaways)
            components.append(disnake.ui.ActionRow(select))

    components.append(disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Giveaways_Painel"),
    ))

    return embed, components

def SpecificGiveawayView_components(inter: disnake.Interaction, giveaway_id: str) -> list[disnake.ui.Container]:
    giveaways = get_giveaways()
    giveaway_data = giveaways.get(giveaway_id)
    if not giveaway_data:
        return EditGiveawayView_components()
        
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
    giveaway_name = giveaway_data.get('name', 'N/A')
    giveaway_mode = giveaway_data.get("mode")
    mode_text = "Não Definido"
    if giveaway_mode == "real":
        mode_text = "Real"
    elif giveaway_mode == "falso":
        mode_text = "Falso"

    log_channel_id = giveaway_data.get('log_channel_id')
    log_channel = inter.bot.get_channel(log_channel_id) if log_channel_id else None
    
    status_text = (
        f"{emoji.giveaway} **Modo de Sorteio:** `{mode_text}`\n"
        f"{emoji.receipt} **Canal de Logs:** {log_channel.mention if log_channel else '`Não Definido`'}\n"
    )
    
    container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > Editar > **{giveaway_name}**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(status_text),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                 disnake.ui.Button(label="Gerenciar Tarefas", style=disnake.ButtonStyle.green, emoji=emoji.reload, custom_id=f"GiveawayEdit_ManageTasks_{giveaway_id}"),
                disnake.ui.Button(label="Gerenciar Preferências", style=disnake.ButtonStyle.grey, emoji=emoji.settings2, custom_id=f"GiveawayEdit_Preferences_{giveaway_id}"),
            ),
            disnake.ui.ActionRow(
                 disnake.ui.Button(label="Definir Logs", style=disnake.ButtonStyle.grey, emoji=emoji.receipt, custom_id=f"GiveawayEdit_SetLogs_{giveaway_id}"),
                 disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.blurple, emoji=emoji.message, custom_id=f"GiveawayEdit_SetMessage_{giveaway_id}"),
                 disnake.ui.Button(label="Configurar Rifa", style=disnake.ButtonStyle.grey, emoji=emoji.dollar, custom_id=f"GiveawayEdit_Rifa_{giveaway_id}"),
            ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Giveaways_VerSorteios"),
        disnake.ui.Button(label="Apagar Sorteio", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"GiveawayEdit_Delete_{giveaway_id}")
    )
    
    return [container, buttons]

def SpecificGiveawayView_embed(inter: disnake.Interaction, giveaway_id: str):
    giveaways = get_giveaways()
    giveaway_data = giveaways.get(giveaway_id)
    if not giveaway_data:
        return EditGiveawayView_embed(inter)
        
    primary_color_hex = db.get_document("custom_colors").get("primary")
    giveaway_name = giveaway_data.get('name', 'N/A')
    giveaway_mode = giveaway_data.get("mode")
    mode_text = "Não Definido"
    if giveaway_mode == "real":
        mode_text = "Real"
    elif giveaway_mode == "falso":
        mode_text = "Falso"

    log_channel_id = giveaway_data.get('log_channel_id')
    log_channel = inter.bot.get_channel(log_channel_id) if log_channel_id else None

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Editando Sorteio: {giveaway_name}",
        **embed_kwargs
    )
    
    status_text = (
        f"{emoji.giveaway} **Modo de Sorteio:** `{mode_text}`\n"
        f"{emoji.receipt} **Canal de Logs:** {log_channel.mention if log_channel else '`Não Definido`'}\n"
    )

    embed.add_field(name="Status:", value=status_text, inline=False)
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Gerenciar Tarefas", style=disnake.ButtonStyle.green, emoji=emoji.reload, custom_id=f"GiveawayEdit_ManageTasks_{giveaway_id}"),
            disnake.ui.Button(label="Gerenciar Preferências", style=disnake.ButtonStyle.grey, emoji=emoji.settings2, custom_id=f"GiveawayEdit_Preferences_{giveaway_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Logs", style=disnake.ButtonStyle.grey, emoji=emoji.receipt, custom_id=f"GiveawayEdit_SetLogs_{giveaway_id}"),
            disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.blurple, emoji=emoji.message, custom_id=f"GiveawayEdit_SetMessage_{giveaway_id}"),
            disnake.ui.Button(label="Configurar Rifa", style=disnake.ButtonStyle.grey, emoji=emoji.dollar, custom_id=f"GiveawayEdit_Rifa_{giveaway_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Giveaways_VerSorteios"),
            disnake.ui.Button(label="Apagar Sorteio", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"GiveawayEdit_Delete_{giveaway_id}")
        )
    ]

    return embed, components

def LogChannelSelectView_components(giveaway_id: str) -> list[disnake.ui.Container]:
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Sorteios > Editar > **Definir Canal de Logs**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione um canal...",
                    custom_id=f"GiveawayEdit_SelectLogChannel_{giveaway_id}",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}")
    )
    
    return [container, buttons]

def LogChannelSelectView_embed(inter: disnake.Interaction, giveaway_id: str):
    primary_color_hex = db.get_document("custom_colors").get("primary")

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Definir Canal de Logs",
        description="Selecione o canal onde os logs do sorteio serão enviados.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Selecione um canal...",
                custom_id=f"GiveawayEdit_SelectLogChannel_{giveaway_id}",
                channel_types=[disnake.ChannelType.text],
                min_values=1,
                max_values=1,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}")
        )
    ]

    return embed, components
