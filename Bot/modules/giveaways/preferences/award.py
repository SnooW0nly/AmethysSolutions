import disnake
from functions.database import database as db
from functions.emoji import emoji
from ..config_giveaways import get_giveaways
from tasks.giveaways.logger_giveaways import log_giveaway_event

class PrizeContentModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.Interaction, giveaway_id: str, current_content: str = ""):
        self.inter = inter
        self.giveaway_id = giveaway_id

        components = [
            disnake.ui.TextInput(
                label="Conteúdo para a DM do Vencedor",
                custom_id="prize_content",
                style=disnake.TextInputStyle.paragraph,
                value=current_content,
                placeholder="Ex: Parabéns! Você ganhou um Nitro Gaming. Resgate seu prêmio aqui: ...",
                max_length=2000,
                required=True
            ),
        ]
        super().__init__(title="Definir Conteúdo da Premiação", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        content = inter.text_values["prize_content"]
        
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id, {})
        
        if "prize" not in giveaway:
            giveaway["prize"] = {}
            
        giveaway["prize"]["content"] = content
        db.salvar("database/giveaways/giveaways_data.json", config)
        
        await log_giveaway_event(
            bot=inter.bot,
            giveaway_id=self.giveaway_id,
            title="Sorteios - Premiação Alterada",
            lines=[
                f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                f"{emoji.edit} **Ação:** Conteúdo da premiação definido.",
                f"{emoji.member} **Executor:** {inter.author.mention}"
            ]
        )
        
        await inter.response.send_message(f"{emoji.correct} Conteúdo da premiação salvo!", ephemeral=True)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await self.inter.edit_original_message(components=PrizeView_components(self.inter, self.giveaway_id))
        else:
            embed, components = PrizeView_embed(self.inter, self.giveaway_id)
            await self.inter.edit_original_message(embed=embed, components=components)

def PrizeView_components(inter: disnake.Interaction, giveaway_id: str) -> list[disnake.ui.Container]:
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    prize_data = giveaway_data.get("prize", {})
    prize_type = prize_data.get("type", "none")

    if prize_type == "none":
        dm_notify = prize_data.get("dm_notify", True)
        status_text = f"{emoji.receipt} **Tipo Atual:** `Nada será entregue`\n{emoji.warn} **Aviso na DM:** `{'Ativado' if dm_notify else 'Desativado'}`"
    elif prize_type == "content":
        content = prize_data.get("content")
        status_text = f"{emoji.receipt} **Tipo Atual:** `Conteúdo na DM`\n{emoji.arrow} **Conteúdo Definido:** `{'Sim' if content else 'Não'}`"
    else: # product
        status_text = f"{emoji.receipt} **Tipo Atual:** `Produto da Loja` (desativado)"

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    options = [
        disnake.SelectOption(label="Nada será entregue", value="none", emoji=emoji.gift, default=prize_type == "none", description="O vencedor será apenas mencionado no canal de anúncio."),
        disnake.SelectOption(label="Conteúdo na DM", value="content", emoji=emoji.message, default=prize_type == "content", description="O vencedor receberá o conteúdo pré-definido em sua DM."),
        disnake.SelectOption(label="Produto da Loja", value="product", emoji=emoji.store, description="Em breve..."),
    ]

    select = disnake.ui.StringSelect(
        placeholder="Selecione um tipo de premiação...",
        options=options,
        custom_id=f"GiveawayPrize_SelectType_{giveaway_id}"
    )
    
    action_rows = [disnake.ui.ActionRow(select)]

    if prize_type == "none":
        dm_notify = prize_data.get("dm_notify", True)
        action_rows.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="Avisar Vencedor na DM", custom_id=f"GiveawayPrize_ToggleDmNotify_{giveaway_id}", style=disnake.ButtonStyle.success if dm_notify else disnake.ButtonStyle.secondary, emoji=emoji.on if dm_notify else emoji.off)
        ))
    elif prize_type == "content":
        action_rows.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Conteúdo da DM", custom_id=f"GiveawayPrize_SetContent_{giveaway_id}", style=disnake.ButtonStyle.blurple, emoji=emoji.edit)
        ))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > **Definir Premiação**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        *action_rows,
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayPref_BackToPreferences_{giveaway_id}")
    )

    return [container, buttons]

def PrizeView_embed(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    prize_data = giveaway_data.get("prize", {})
    prize_type = prize_data.get("type", "none")

    if prize_type == "none":
        dm_notify = prize_data.get("dm_notify", True)
        description = f"{emoji.receipt} **Tipo Atual:** `Nada será entregue`\n{emoji.warn} **Aviso na DM:** `{'Ativado' if dm_notify else 'Desativado'}`"
    elif prize_type == "content":
        content = prize_data.get("content")
        description = f"{emoji.receipt} **Tipo Atual:** `Conteúdo na DM`\n{emoji.arrow} **Conteúdo Definido:** `{'Sim' if content else 'Não'}`"
    else: # product
        description = f"{emoji.receipt} **Tipo Atual:** `Produto da Loja` (desativado)"

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(title=f"Definir Premiação: {giveaway_name}", description=description, **embed_kwargs)
    
    options = [
        disnake.SelectOption(label="Nada será entregue", value="none", emoji=emoji.gift, default=prize_type == "none", description="O vencedor será apenas mencionado no canal de anúncio."),
        disnake.SelectOption(label="Conteúdo na DM", value="content", emoji=emoji.message, default=prize_type == "content", description="O vencedor receberá o conteúdo pré-definido em sua DM."),
        disnake.SelectOption(label="Produto da Loja", value="product", emoji=emoji.store, description="Em breve..."),
    ]

    select = disnake.ui.StringSelect(
        placeholder="Selecione um tipo de premiação...",
        options=options,
        custom_id=f"GiveawayPrize_SelectType_{giveaway_id}"
    )

    components = [disnake.ui.ActionRow(select)]

    if prize_type == "none":
        dm_notify = prize_data.get("dm_notify", True)
        components.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="Avisar Vencedor na DM", custom_id=f"GiveawayPrize_ToggleDmNotify_{giveaway_id}", style=disnake.ButtonStyle.success if dm_notify else disnake.ButtonStyle.secondary, emoji=emoji.on if dm_notify else emoji.off)
        ))
    elif prize_type == "content":
        components.append(disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Conteúdo da DM", custom_id=f"GiveawayPrize_SetContent_{giveaway_id}", style=disnake.ButtonStyle.blurple, emoji=emoji.edit)
        ))

    components.append(disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayPref_BackToPreferences_{giveaway_id}")
    ))

    return embed, components
