import disnake
from functions.database import database as db
from functions.emoji import emoji
from ..config_giveaways import get_giveaways

# --- Main Roles Panel ---

def RolesView_components(inter: disnake.Interaction, giveaway_id: str) -> list[disnake.ui.Container]:
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    
    allowed_count = len(giveaway_data.get("allowed_roles", []))
    forbidden_count = len(giveaway_data.get("forbidden_roles", []))
    bonus_count = len(giveaway_data.get("bonus_roles", {}))

    status_text = (
        f"{emoji.double_check} **Cargos Permitidos:** `{allowed_count}` cargos configurados\n"
        f"{emoji.wrong} **Cargos Proibidos:** `{forbidden_count}` cargos configurados\n"
        f"{emoji.plus} **Cargos com Bônus:** `{bonus_count}` cargos configurados"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > **Definir Cargos**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Cargos Permitidos", style=disnake.ButtonStyle.green, emoji=emoji.double_check, custom_id=f"GiveawayRoles_Allowed_{giveaway_id}"),
            disnake.ui.Button(label="Cargos Proibidos", style=disnake.ButtonStyle.danger, emoji=emoji.wrong, custom_id=f"GiveawayRoles_Forbidden_{giveaway_id}"),
            disnake.ui.Button(label="Cargos com Bônus", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id=f"GiveawayRoles_Bonus_{giveaway_id}"),
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayPref_BackToPreferences_{giveaway_id}")
    )

    return [container, buttons]

def RolesView_embed(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")

    allowed_count = len(giveaway_data.get("allowed_roles", []))
    forbidden_count = len(giveaway_data.get("forbidden_roles", []))
    bonus_count = len(giveaway_data.get("bonus_roles", {}))

    description = (
        f"{emoji.double_check} **Cargos Permitidos:** `{allowed_count}` cargos configurados\n"
        f"{emoji.wrong} **Cargos Proibidos:** `{forbidden_count}` cargos configurados\n"
        f"{emoji.plus} **Cargos com Bônus:** `{bonus_count}` cargos configurados"
    )

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(title=f"Definir Cargos: {giveaway_name}", description=description, **embed_kwargs)
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Cargos Permitidos", style=disnake.ButtonStyle.green, emoji=emoji.double_check, custom_id=f"GiveawayRoles_Allowed_{giveaway_id}"),
            disnake.ui.Button(label="Cargos Proibidos", style=disnake.ButtonStyle.danger, emoji=emoji.wrong, custom_id=f"GiveawayRoles_Forbidden_{giveaway_id}"),
            disnake.ui.Button(label="Cargos com Bônus", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id=f"GiveawayRoles_Bonus_{giveaway_id}"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayPref_BackToPreferences_{giveaway_id}")
        )
    ]
    return embed, components


# --- Allowed Roles ---

def AllowedRolesView_components(inter: disnake.Interaction, giveaway_id: str, giveaway_name: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    allowed_roles = giveaway_data.get("allowed_roles", [])
    
    selected_roles_text = "\n".join(
        f"∙ {inter.guild.get_role(r).mention}"
        for r in allowed_roles if inter.guild.get_role(r)
    ) or "Nenhum cargo permitido configurado."

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > Cargos > **Cargos Permitidos**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay("Selecione abaixo para adicionar ou remover cargos da lista."),
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                placeholder="Selecione os cargos permitidos...",
                custom_id=f"GiveawayRoles_SelectAllowed_{giveaway_id}",
                min_values=0, max_values=25,
                default_values=[disnake.Object(id=r) for r in allowed_roles]
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_BackToPanel_{giveaway_id}")
    )
    return [container, buttons]

def AllowedRolesView_embed(inter: disnake.Interaction, giveaway_id: str, giveaway_name: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    allowed_roles = giveaway_data.get("allowed_roles", [])
    
    selected_roles_text = "\n".join(
        f"∙ {inter.guild.get_role(r).mention}"
        for r in allowed_roles if inter.guild.get_role(r)
    ) or "Nenhum cargo permitido configurado."

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
        
    embed = disnake.Embed(
        title=f"Cargos Permitidos: {giveaway_name}",
        description=selected_roles_text,
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                placeholder="Selecione os cargos permitidos",
                custom_id=f"GiveawayRoles_SelectAllowed_{giveaway_id}",
                min_values=0, max_values=25,
                default_values=[disnake.Object(id=r) for r in allowed_roles]
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_BackToPanel_{giveaway_id}")
        )
    ]
    return embed, components


# --- Forbidden Roles ---

def ForbiddenRolesView_components(inter: disnake.Interaction, giveaway_id: str, giveaway_name: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    forbidden_roles = giveaway_data.get("forbidden_roles", [])
    
    selected_roles_text = "\n".join(
        f"∙ {inter.guild.get_role(r).mention}"
        for r in forbidden_roles if inter.guild.get_role(r)
    ) or "Nenhum cargo proibido configurado."
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > Cargos > **Cargos Proibidos**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay("Selecione abaixo para adicionar ou remover cargos da lista."),
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                placeholder="Selecione os cargos proibidos",
                custom_id=f"GiveawayRoles_SelectForbidden_{giveaway_id}",
                min_values=0, max_values=25,
                default_values=[disnake.Object(id=r) for r in forbidden_roles]
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_BackToPanel_{giveaway_id}")
    )
    return [container, buttons]

def ForbiddenRolesView_embed(inter: disnake.Interaction, giveaway_id: str, giveaway_name: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    forbidden_roles = giveaway_data.get("forbidden_roles", [])
    
    selected_roles_text = "\n".join(
        f"∙ {inter.guild.get_role(r).mention}"
        for r in forbidden_roles if inter.guild.get_role(r)
    ) or "Nenhum cargo proibido configurado."

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
        
    embed = disnake.Embed(
        title=f"Cargos Proibidos: {giveaway_name}",
        description=selected_roles_text,
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                placeholder="Selecione os cargos proibidos",
                custom_id=f"GiveawayRoles_SelectForbidden_{giveaway_id}",
                min_values=0, max_values=25,
                default_values=[disnake.Object(id=r) for r in forbidden_roles]
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_BackToPanel_{giveaway_id}")
        )
    ]
    return embed, components


# --- Bonus Roles ---

class BonusEntriesModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.Interaction, giveaway_id: str, role_id: str, current_entries: str):
        self.inter = inter
        self.giveaway_id = giveaway_id
        self.role_id = role_id

        components = [
            disnake.ui.TextInput(
                label="Número de Entradas Bônus", custom_id="bonus_entries",
                value=current_entries, placeholder="Ex: 2", min_length=1, max_length=2, required=True
            ),
        ]
        super().__init__(title="Definir Entradas Bônus", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id, {})
        giveaway_name = giveaway.get("name", "N/A")
        
        try:
            entries = int(inter.text_values["bonus_entries"])
            if entries <= 0: raise ValueError
        except ValueError:
            return await inter.response.send_message("Por favor, insira um número válido e maior que zero.", ephemeral=True)

        if "bonus_roles" not in giveaway:
            giveaway["bonus_roles"] = {}
        
        giveaway["bonus_roles"][self.role_id] = entries
        db.salvar("database/giveaways/giveaways_data.json", config)

        role = inter.guild.get_role(int(self.role_id))
        from tasks.giveaways.logger_giveaways import log_giveaway_event
        await log_giveaway_event(
            bot=inter.bot,
            giveaway_id=self.giveaway_id,
            title="Sorteios - Cargos Alterados",
            lines=[
                f"{emoji.giveaway} **Sorteio:** {giveaway_name}",
                f"{emoji.plus} **Cargo Bônus:** {role.mention if role else self.role_id}",
                f"{emoji.edit} **Entradas Adicionais:** `{entries}`",
                f"{emoji.member} **Executor:** {inter.author.mention}"
            ]
        )

        await inter.response.send_message(f"{emoji.correct} Entradas bônus salvas com sucesso!", ephemeral=True)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await self.inter.edit_original_message(components=BonusRolesView_components(self.inter, self.giveaway_id))
        else:
            embed, components = BonusRolesView_embed(self.inter, self.giveaway_id)
            await self.inter.edit_original_message(embed=embed, components=components)

def BonusRolesView_components(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    bonus_roles = giveaway_data.get("bonus_roles", {})
    description = "\n".join(
        f"{inter.guild.get_role(int(r)).mention}: **+{e} entradas**"
        for r, e in bonus_roles.items() if inter.guild.get_role(int(r))
    ) or "Nenhum cargo bônus configurado."
    
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > Cargos > **Cargos com Bônus**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(description),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar/Editar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id=f"GiveawayRoles_AddBonusRole_{giveaway_id}"),
            disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.danger, emoji=emoji.delete, custom_id=f"GiveawayRoles_RemoveBonusRole_{giveaway_id}", disabled=not bonus_roles),
        ),
        **container_kwargs
    )

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_BackToPanel_{giveaway_id}")
    )
    return [container, buttons]

def BonusRolesView_embed(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    bonus_roles = giveaway_data.get("bonus_roles", {})
    description = "\n".join(
        f"{inter.guild.get_role(int(r)).mention}: **+{e} entradas**"
        for r, e in bonus_roles.items() if inter.guild.get_role(int(r))
    ) or "Nenhum cargo bônus configurado."
        
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(title=f"Cargos com Bônus: {giveaway_name}", description=description, **embed_kwargs)
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar/Editar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id=f"GiveawayRoles_AddBonusRole_{giveaway_id}"),
            disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.danger, emoji=emoji.delete, custom_id=f"GiveawayRoles_RemoveBonusRole_{giveaway_id}", disabled=not bonus_roles),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_BackToPanel_{giveaway_id}")
        )
    ]
    return embed, components

def SelectBonusRoleView_components(giveaway_id: str, giveaway_name: str):
    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > Cargos > Bônus > **Selecionar Cargo**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                placeholder="Selecione um cargo...",
                custom_id=f"GiveawayRoles_SelectBonusRole_{giveaway_id}",
                min_values=1, max_values=1
            )
        ),
        **container_kwargs
    )
    buttons = disnake.ui.ActionRow(
         disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_Bonus_{giveaway_id}")
    )
    return [container, buttons]

def SelectBonusRoleView_embed(giveaway_id: str, giveaway_name: str):
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
        
    embed = disnake.Embed(
        title=f"Selecionar Cargo Bônus: {giveaway_name}",
        description="Selecione o cargo ao qual você deseja adicionar entradas bônus.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.RoleSelect(
                placeholder="Selecione um cargo para adicionar/editar...",
                custom_id=f"GiveawayRoles_SelectBonusRole_{giveaway_id}",
                min_values=1, max_values=1
            )
        ),
        disnake.ui.ActionRow(
             disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_Bonus_{giveaway_id}")
        )
    ]
    return embed, components

def RemoveBonusRoleView_components(inter: disnake.Interaction, giveaway_id: str, giveaway_name: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    bonus_roles = giveaway_data.get("bonus_roles", {})
    
    options = []
    for role_id in bonus_roles:
        role = inter.guild.get_role(int(role_id))
        if role:
            options.append(disnake.SelectOption(label=role.name, value=str(role.id)))

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
    
    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > Cargos > Bônus > **Remover Cargos**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay("Selecione um ou mais cargos para remover."),
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder="Selecione os cargos para remover...",
                custom_id=f"GiveawayRoles_SelectRemoveBonusRole_{giveaway_id}",
                min_values=1, max_values=len(options) if options else 1,
                options=options if options else [disnake.SelectOption(label="Nenhum cargo configurado", value="disabled")],
                disabled=not options
            )
        ),
        **container_kwargs
    )
    buttons = disnake.ui.ActionRow(
         disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_Bonus_{giveaway_id}")
    )
    return [container, buttons]

def RemoveBonusRoleView_embed(inter: disnake.Interaction, giveaway_id: str, giveaway_name: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    bonus_roles = giveaway_data.get("bonus_roles", {})
    
    options = []
    for role_id in bonus_roles:
        role = inter.guild.get_role(int(role_id))
        if role:
            options.append(disnake.SelectOption(label=role.name, value=str(role.id)))
            
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Remover Cargos Bônus: {giveaway_name}",
        description="Selecione um ou mais cargos para remover da lista de bônus.",
        **embed_kwargs
    )
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder="Selecione os cargos para remover...",
                custom_id=f"GiveawayRoles_SelectRemoveBonusRole_{giveaway_id}",
                min_values=1, max_values=len(options) if options else 1,
                options=options if options else [disnake.SelectOption(label="Nenhum cargo configurado", value="disabled")],
                disabled=not options
            )
        ),
        disnake.ui.ActionRow(
             disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayRoles_Bonus_{giveaway_id}")
        )
    ]
    return embed, components
