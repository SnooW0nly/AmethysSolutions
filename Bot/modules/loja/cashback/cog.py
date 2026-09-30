"""
Sistema de Cashback - Cog principal
"""
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .manager import CashbackManager


class CashbackSystem(commands.Cog):
    """Sistema de Cashback"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def panel(self, inter: disnake.MessageInteraction) -> dict:
        """Retorna o painel de configuração do cashback"""
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return self._panel_embed(inter)
        return self._panel_components(inter)
    
    def _panel_components(self, inter: disnake.MessageInteraction) -> dict:
        """Painel em modo componentes"""
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        config = CashbackManager._get_config()
        enabled = config.get("enabled", False)
        balance_enabled = CashbackManager.is_balance_enabled()
        percentage = config.get("default_percentage", 5.0)
        rules = config.get("rules", [])
        
        # Status do sistema
        if not balance_enabled:
            status_text = f"{emoji.wrong} **Sistema de Saldo desativado** - Ative primeiro o sistema de saldo."
        elif enabled:
            status_text = f"{emoji.correct} **Cashback Ativo** - Porcentagem: `{percentage}%`"
        else:
            status_text = f"{emoji.wrong} **Cashback Desativado**"
        
        # Regras
        rules_text = ""
        if rules:
            rules_list = []
            for rule in rules:
                rules_list.append(f"• <@&{rule['role_id']}>: `{rule['multiplier']}x`")
            rules_text = f"\n\n**Regras por Cargo:**\n" + "\n".join(rules_list)
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > **Cashback**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{status_text}\n"
                    f"-# O cashback é creditado automaticamente no saldo."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Desativar" if enabled else "Ativar",
                        emoji=emoji.wrong if enabled else emoji.correct,
                        style=disnake.ButtonStyle.danger if enabled else disnake.ButtonStyle.success,
                        custom_id="Cashback_Toggle",
                        disabled=not balance_enabled
                    ),
                    disnake.ui.Button(
                        label="Porcentagem",
                        emoji=emoji.dollar,
                        style=disnake.ButtonStyle.grey,
                        custom_id="Cashback_Percentage"
                    ),
                    disnake.ui.Button(
                        label="Regras",
                        emoji=emoji.textc,
                        style=disnake.ButtonStyle.grey,
                        custom_id="Cashback_Rules"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    emoji=emoji.back,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Loja_Panel"
                )
            )
        ]}
    
    def _panel_embed(self, inter: disnake.MessageInteraction) -> dict:
        """Painel em modo embed"""
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        embed_kwargs = {}
        if primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
        
        config = CashbackManager._get_config()
        enabled = config.get("enabled", False)
        balance_enabled = CashbackManager.is_balance_enabled()
        percentage = config.get("default_percentage", 5.0)
        rules = config.get("rules", [])
        
        # Status
        if not balance_enabled:
            status_text = f"{emoji.wrong} **Sistema de Saldo desativado** - Ative primeiro o sistema de saldo."
        elif enabled:
            status_text = f"{emoji.correct} **Cashback Ativo** - Porcentagem: `{percentage}%`"
        else:
            status_text = f"{emoji.wrong} **Cashback Desativado**"
        
        # Regras
        rules_text = ""
        if rules:
            rules_list = []
            for rule in rules:
                rules_list.append(f"• <@&{rule['role_id']}>: `{rule['multiplier']}x`")
            rules_text = f"\n\n**Regras por Cargo:**\n" + "\n".join(rules_list)
        
        embed = disnake.Embed(
            title=f"{emoji.bank}",
            description=(
                f"{status_text}\n"
                f"-# O cashback é creditado automaticamente no saldo."
            ),
            **embed_kwargs
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Desativar" if enabled else "Ativar",
                    emoji=emoji.wrong if enabled else emoji.correct,
                    style=disnake.ButtonStyle.danger if enabled else disnake.ButtonStyle.success,
                    custom_id="Cashback_Toggle",
                    disabled=not balance_enabled
                ),
                disnake.ui.Button(
                    label="Porcentagem",
                    emoji=emoji.dollar,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Cashback_Percentage"
                ),
                disnake.ui.Button(
                    label="Regras",
                    emoji=emoji.textc,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Cashback_Rules"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    emoji=emoji.back,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Loja_Panel"
                )
            )
        ]
        
        return {"embed": embed, "components": components}

    def _rules_panel(self, inter: disnake.MessageInteraction) -> dict:
        """Painel de regras"""
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        rules = CashbackManager.get_rules()
        
        rules_text = "-# Nenhuma regra configurada."
        if rules:
            rules_list = []
            for rule in rules:
                rules_list.append(f"• <@&{rule['role_id']}>: `{rule['multiplier']}x`")
            rules_text = "\n".join(rules_list)
        
        if mode == "components":
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            return {"components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Cashback > **Regras**"),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.StringSelect(
                            placeholder="Selecione uma regra para configurar",
                            custom_id="Cashback_RuleSelect",
                            options=[
                                disnake.SelectOption(
                                    label="Cashback por Cargo",
                                    value="role_cashback",
                                    emoji=emoji.members,
                                    description="Multiplicador de cashback por cargo"
                                )
                            ]
                        )
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"**Regras Ativas:**\n{rules_text}"
                    ),
                    **container_kwargs
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        emoji=emoji.back,
                        style=disnake.ButtonStyle.grey,
                        custom_id="Cashback_Back"
                    )
                )
            ]}
        else:
            embed = disnake.Embed(
                title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}",
                description=f"-# Painel > Loja > Cashback > **Regras**\n\n**Regras Ativas:**\n{rules_text}",
                color=int(primary_color_hex.replace("#", ""), 16) if primary_color_hex else disnake.Color.blue()
            )
            
            return {"embed": embed, "components": [
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione uma regra para configurar",
                        custom_id="Cashback_RuleSelect",
                        options=[
                            disnake.SelectOption(
                                label="Cashback por Cargo",
                                value="role_cashback",
                                emoji=emoji.members,
                                description="Multiplicador de cashback por cargo"
                            )
                        ]
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        emoji=emoji.back,
                        style=disnake.ButtonStyle.grey,
                        custom_id="Cashback_Back"
                    )
                )
            ]}

    def _role_rules_panel(self, inter: disnake.MessageInteraction) -> dict:
        """Painel de regras por cargo"""
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        rules = CashbackManager.get_rules()
        
        rules_text = "-# Nenhuma regra de cargo configurada."
        if rules:
            rules_list = []
            for rule in rules:
                rules_list.append(f"• <@&{rule['role_id']}>: `{rule['multiplier']}x`")
            rules_text = "\n".join(rules_list)
        
        if mode == "components":
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            return {"components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Cashback > Regras > **Cargo**"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"Defina multiplicadores de cashback por cargo.\n"
                        f"Exemplo: `2x` com 5% de cashback = 10%\n\n"
                        f"**Cargos Configurados:**\n{rules_text}"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Adicionar Cargo",
                            emoji=emoji.plus,
                            style=disnake.ButtonStyle.success,
                            custom_id="Cashback_AddRole"
                        ),
                        disnake.ui.Button(
                            label="Remover Cargo",
                            emoji=emoji.minus,
                            style=disnake.ButtonStyle.danger,
                            custom_id="Cashback_RemoveRole",
                            disabled=len(rules) == 0
                        )
                    ),
                    **container_kwargs
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        emoji=emoji.back,
                        style=disnake.ButtonStyle.grey,
                        custom_id="Cashback_BackToRules"
                    )
                )
            ]}
        else:
            embed = disnake.Embed(
                title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}",
                description=(
                    f"-# Painel > Loja > Cashback > Regras > **Cargo**\n\n"
                    f"Defina multiplicadores de cashback por cargo.\n"
                    f"Exemplo: `2x` com 5% de cashback = 10%\n\n"
                    f"**Cargos Configurados:**\n{rules_text}"
                ),
                color=int(primary_color_hex.replace("#", ""), 16) if primary_color_hex else disnake.Color.blue()
            )
            
            return {"embed": embed, "components": [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Cargo",
                        emoji=emoji.plus,
                        style=disnake.ButtonStyle.success,
                        custom_id="Cashback_AddRole"
                    ),
                    disnake.ui.Button(
                        label="Remover Cargo",
                        emoji=emoji.minus,
                        style=disnake.ButtonStyle.danger,
                        custom_id="Cashback_RemoveRole",
                        disabled=len(rules) == 0
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        emoji=emoji.back,
                        style=disnake.ButtonStyle.grey,
                        custom_id="Cashback_BackToRules"
                    )
                )
            ]}
    
    @commands.Cog.listener("on_button_click")
    async def on_cashback_button(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if not custom_id.startswith("Cashback_"):
            return
        
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        
        # Toggle ativar/desativar
        if custom_id == "Cashback_Toggle":
            config = CashbackManager._get_config()
            new_status = not config.get("enabled", False)
            
            success, error_message = CashbackManager.set_enabled(new_status)
            
            if not success:
                await inter.response.send_message(
                    f"{emoji.wrong} {error_message}",
                    ephemeral=True
                )
                return
            
            # Atualizar painel
            await msg_handler.wait(inter, send=False)
            panel_data = self.panel(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Modal de porcentagem
        elif custom_id == "Cashback_Percentage":
            current = CashbackManager.get_default_percentage()
            modal = disnake.ui.Modal(
                title="Porcentagem de Cashback",
                custom_id="cashback_percentage_modal",
                components=[
                    disnake.ui.TextInput(
                        label="Porcentagem de cashback (%)",
                        placeholder="Ex: 5",
                        custom_id="percentage",
                        value=str(current),
                        required=True,
                        max_length=5
                    )
                ]
            )
            await inter.response.send_modal(modal)
        
        # Painel de regras
        elif custom_id == "Cashback_Rules":
            await msg_handler.wait(inter, send=False)
            panel_data = self._rules_panel(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Voltar ao painel principal
        elif custom_id == "Cashback_Back":
            await msg_handler.wait(inter, send=False)
            panel_data = self.panel(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Voltar ao painel de regras
        elif custom_id == "Cashback_BackToRules":
            await msg_handler.wait(inter, send=False)
            panel_data = self._rules_panel(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Adicionar cargo
        elif custom_id == "Cashback_AddRole":
            modal = disnake.ui.Modal(
                title="Adicionar Cargo",
                custom_id="cashback_add_role_modal",
                components=[
                    disnake.ui.TextInput(
                        label="ID do Cargo",
                        placeholder="Ex: 1234567890123456789",
                        custom_id="role_id",
                        required=True,
                        max_length=20
                    ),
                    disnake.ui.TextInput(
                        label="Multiplicador de Cashback",
                        placeholder="Ex: 2 (para 2x o cashback normal)",
                        custom_id="multiplier",
                        required=True,
                        max_length=5
                    )
                ]
            )
            await inter.response.send_modal(modal)
        
        # Remover cargo
        elif custom_id == "Cashback_RemoveRole":
            rules = CashbackManager.get_rules()
            if not rules:
                await inter.response.send_message(
                    f"{emoji.wrong} Não há regras para remover.",
                    ephemeral=True
                )
                return
            
            options = []
            for rule in rules:
                options.append(
                    disnake.SelectOption(
                        label=rule.get("role_name", f"Cargo {rule['role_id']}"),
                        value=rule["role_id"],
                        description=f"Multiplicador: {rule['multiplier']}x"
                    )
                )
            
            await inter.response.send_message(
                f"{emoji.warn} Selecione o cargo para remover:",
                components=[
                    disnake.ui.ActionRow(
                        disnake.ui.StringSelect(
                            placeholder="Selecione um cargo",
                            custom_id="Cashback_SelectRemoveRole",
                            options=options
                        )
                    )
                ],
                ephemeral=True
            )
    
    @commands.Cog.listener("on_dropdown")
    async def on_cashback_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if not custom_id.startswith("Cashback_"):
            return
        
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        
        # Seleção de tipo de regra
        if custom_id == "Cashback_RuleSelect":
            value = inter.values[0]
            
            if value == "role_cashback":
                await msg_handler.wait(inter, send=False)
                panel_data = self._role_rules_panel(inter)
                if "embed" in panel_data:
                    await inter.edit_original_message(content=None, **panel_data)
                else:
                    await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Remover cargo
        elif custom_id == "Cashback_SelectRemoveRole":
            role_id = inter.values[0]
            success = CashbackManager.remove_rule(int(role_id))
            
            if success:
                await inter.response.send_message(
                    f"{emoji.correct} Regra removida!",
                    ephemeral=True
                )
            else:
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao remover regra.",
                    ephemeral=True
                )
    
    @commands.Cog.listener("on_modal_submit")
    async def on_cashback_modal(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        
        if not custom_id.startswith("cashback_"):
            return
        
        # Modal de porcentagem
        if custom_id == "cashback_percentage_modal":
            try:
                percentage = float(inter.text_values["percentage"].replace(",", "."))
                
                if percentage < 0 or percentage > 100:
                    await inter.response.send_message(
                        f"{emoji.wrong} A porcentagem deve estar entre 0 e 100.",
                        ephemeral=True
                    )
                    return
                
                CashbackManager.set_default_percentage(percentage)
                
                # Editar o painel principal com as novas informações
                mode = db.get_document("custom_mode").get("mode")
                msg_handler = embed_message if mode == "embed" else message
                await msg_handler.wait(inter, send=False)
                
                # Buscar a mensagem original do painel cashback
                from .cog import CashbackSystem
                cashback_system = CashbackSystem(inter.bot)
                panel_data = cashback_system.panel(inter)
                
                if "embed" in panel_data:
                    await inter.edit_original_message(content=None, **panel_data)
                else:
                    await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.wrong} Valor inválido. Use apenas números.",
                    ephemeral=True
                )
        
        # Modal de adicionar cargo
        elif custom_id == "cashback_add_role_modal":
            try:
                role_id = int(inter.text_values["role_id"])
                multiplier = float(inter.text_values["multiplier"].replace(",", "."))
                
                if multiplier <= 0:
                    await inter.response.send_message(
                        f"{emoji.wrong} O multiplicador deve ser maior que 0.",
                        ephemeral=True
                    )
                    return
                
                # Tentar obter nome do cargo
                role = inter.guild.get_role(role_id)
                role_name = role.name if role else f"Cargo {role_id}"
                
                success = CashbackManager.add_rule(role_id, role_name, multiplier)
                
                if success:
                    await inter.response.send_message(
                        f"{emoji.correct} Cargo <@&{role_id}> adicionado com `{multiplier}x` cashback!",
                        ephemeral=True
                    )
                else:
                    await inter.response.send_message(
                        f"{emoji.wrong} Erro ao adicionar cargo.",
                        ephemeral=True
                    )
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.wrong} Valores inválidos. Use apenas números.",
                    ephemeral=True
                )


def setup(bot: commands.Bot):
    bot.add_cog(CashbackSystem(bot))
