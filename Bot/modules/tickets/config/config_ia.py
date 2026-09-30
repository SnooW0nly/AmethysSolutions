import disnake
from functions.database import database as db
from functions.emoji import emoji
from .edit_panel import SpecificPanelView_components, SpecificPanelView_embed

class EditIAPromptModal(disnake.ui.Modal):
    def __init__(self, panel_id: str):
        self.panel_id = panel_id
        
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id, {})
        current_prompt = panel_data.get("ai_prompt", "")
        is_ai_use_context = panel_data.get("ai_use_context", False)

        components = [
            disnake.ui.TextInput(
                label="Instruções Adicionais para a IA",
                custom_id="ai_prompt",
                value=current_prompt,
                style=disnake.TextInputStyle.paragraph,
                max_length=4000
            ),
            disnake.ui.TextInput(
                label="Usar Contexto (Sim/Não)",
                custom_id="ai_use_context",
                value="Sim" if is_ai_use_context else "Não",
                style=disnake.TextInputStyle.short,
                max_length=3,
                min_length=3,
                placeholder="Digite 'Sim' para ativar ou 'Não' para desativar."
            ),
        ]
        super().__init__(title="Editar Instruções da AmethysAI", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        if self.panel_id not in config.get("panels", {}): return
        
        # Salvar prompt completo no DB (sem truncamento)
        prompt = inter.text_values.get("ai_prompt") or ""
        config["panels"][self.panel_id]["ai_prompt"] = prompt
        
        use_context_str = inter.text_values.get("ai_use_context", "Não").lower()
        use_context = use_context_str.strip() in ["sim", "s"]
        config["panels"][self.panel_id]["ai_use_context"] = use_context

        db.save_document("tickets_config", config)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=ConfigIAView_components(inter, self.panel_id))
        else:
            embed, components = ConfigIAView_embed(inter, self.panel_id)
            await inter.response.edit_message(content=None, embed=embed, components=components)

def ConfigIAView_components(inter: disnake.Interaction, panel_id: str) -> list:
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id)
    if not panel_data: 
        return SpecificPanelView_components(inter, panel_id)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    is_panel_enabled = panel_data.get("enabled", False)
    is_ai_enabled = panel_data.get("ai_enabled", False)
    is_ai_use_context = panel_data.get("ai_use_context", False)
    
    # Obter prompt completo do DB (não truncar no DB)
    prompt_full = panel_data.get("ai_prompt") or "Nenhuma instrução adicional definida."
    
    # Calcular tamanho dos textos fixos para garantir que o total não exceda 4000 caracteres
    panel_name = panel_data.get('name', '')
    header_text = f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > {panel_name} > **AmethysAI**"
    status_text = (
        f"{emoji.on if is_ai_enabled else emoji.off} **Status:** {'`Ativada`' if is_ai_enabled else '`Desativada`'}\n"
        f"{emoji.on if is_ai_use_context else emoji.off} **Usar Contexto:** {'`Ativado`' if is_ai_use_context else '`Desativado`'}"
    )
    instructions_label = "**Instruções Adicionais:**\n```"
    instructions_suffix = "```"
    
    # Calcular espaço disponível para o prompt (limite total: 4000 caracteres)
    fixed_text_size = len(header_text) + len(status_text) + len(instructions_label) + len(instructions_suffix)
    max_prompt_display_len = max(0, 4000 - fixed_text_size - 50)  # 50 de margem de segurança
    
    # Truncar prompt se necessário
    if len(prompt_full) > max_prompt_display_len:
        prompt_display = prompt_full[:max_prompt_display_len] + "..."
    else:
        prompt_display = prompt_full

    toggle_button = disnake.ui.Button(
        label="",
        style=disnake.ButtonStyle.grey,
        emoji=emoji.power,
        custom_id=f"TicketIA_Toggle_{panel_id}",
        disabled=not is_panel_enabled
    )

    edit_prompt_button = disnake.ui.Button(
        label="Editar Instruções",
        style=disnake.ButtonStyle.blurple,
        emoji=emoji.edit,
        custom_id=f"TicketIA_EditPrompt_{panel_id}",
        disabled=not is_ai_enabled or not is_panel_enabled
    )

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    container = disnake.ui.Container(
            disnake.ui.TextDisplay(header_text),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(status_text),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"{instructions_label}{prompt_display}{instructions_suffix}"),
            disnake.ui.Separator(),
        disnake.ui.ActionRow(toggle_button, edit_prompt_button),
        **container_kwargs
    )

    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
    )
    
    return [container, buttons]

def ConfigIAView_embed(inter: disnake.Interaction, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id)
    if not panel_data: 
        return SpecificPanelView_embed(inter, panel_id)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    is_panel_enabled = panel_data.get("enabled", False)
    is_ai_enabled = panel_data.get("ai_enabled", False)
    is_ai_use_context = panel_data.get("ai_use_context", False)
    
    # Obter prompt completo do DB (não truncar no DB)
    prompt_full = panel_data.get("ai_prompt") or "Nenhuma instrução adicional definida."
    
    status_text = f"{emoji.on if is_ai_enabled else emoji.off} **Status:** {'`Ativada`' if is_ai_enabled else '`Desativada`'}"
    context_text = f"{emoji.on if is_ai_use_context else emoji.off} **Usar Contexto:** {'`Ativado`' if is_ai_use_context else '`Desativado`'}"
    
    header = (
        f"{status_text}\n"
        f"{context_text}\n\n"
        f"**Instruções Adicionais:**\n"
    )
    
    # Truncar apenas para exibição no embed (limite do Discord)
    max_prompt_len = 4096 - len(header) - 9 
    
    if len(prompt_full) > max_prompt_len:
        prompt_display = prompt_full[:max_prompt_len] + "..."
    else:
        prompt_display = prompt_full

    description = f"{header}```{prompt_display}```"

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurar AmethysAI: {panel_data.get('name')}",
        description=description,
        **embed_kwargs
    )
    # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
    # embed.timestamp = disnake.utils.utcnow()

    toggle_button = disnake.ui.Button(
        label="",
        style=disnake.ButtonStyle.grey,
        emoji=emoji.power,
        custom_id=f"TicketIA_Toggle_{panel_id}",
        disabled=not is_panel_enabled
    )

    edit_prompt_button = disnake.ui.Button(
        label="Editar Instruções",
        style=disnake.ButtonStyle.blurple,
        emoji=emoji.edit,
        custom_id=f"TicketIA_EditPrompt_{panel_id}",
        disabled=not is_ai_enabled or not is_panel_enabled
    )
    
    components = [
        disnake.ui.ActionRow(toggle_button, edit_prompt_button),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"TicketEdit_BackToPanel_{panel_id}")
        )
    ]

    return embed, components
