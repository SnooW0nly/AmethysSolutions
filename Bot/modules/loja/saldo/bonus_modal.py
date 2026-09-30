"""
Modal para configurar bônus do sistema de saldo
Usa select menu para escolher o tipo de bônus
"""
import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class BonusModal(disnake.ui.Modal):
    """Modal para configurar o bônus de depósito"""
    
    def __init__(self, config: dict):
        self.config = config
        bonus = config.get("bonus", {})
        current_type = bonus.get("type", "disabled")
        current_value = bonus.get("value", 0)
        
        # Opções do select para tipo de bônus
        type_options = [
            disnake.SelectOption(
                label="Desativado",
                value="disabled",
                emoji=emoji.wrong,
                description="Sem bônus nos depósitos",
                default=current_type == "disabled"
            ),
            disnake.SelectOption(
                label="Porcentagem",
                value="percentage",
                emoji=emoji.chart,
                description="Bônus em % do valor depositado",
                default=current_type == "percentage"
            ),
            disnake.SelectOption(
                label="Valor Fixo",
                value="fixed",
                emoji=emoji.dollar,
                description="Bônus em R$ fixo por depósito",
                default=current_type == "fixed"
            ),
        ]
        
        components = [
            disnake.ui.Label(
                text="Tipo de Bônus",
                component=disnake.ui.StringSelect(
                    placeholder="Selecione o tipo de bônus",
                    custom_id="bonus_type",
                    options=type_options,
                    required=True,
                ),
                description="Como o bônus será calculado"
            ),
            disnake.ui.TextInput(
                label="Valor do Bônus",
                placeholder="Ex: 10 (para 10% ou R$10)",
                custom_id="bonus_value",
                style=disnake.TextInputStyle.short,
                value=str(current_value) if current_value else "",
                required=False,
                max_length=10
            ),
        ]
        
        super().__init__(title="Configurar Bônus de Depósito", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        valores = inter.resolved_values
        
        # Processar tipo do select
        type_value = valores.get("bonus_type")
        if isinstance(type_value, (list, tuple)):
            bonus_type = type_value[0] if type_value else "disabled"
        else:
            bonus_type = type_value or "disabled"
        
        # Processar valor
        value_input = inter.text_values.get("bonus_value", "").strip()
        try:
            bonus_value = float(value_input.replace(",", ".")) if value_input else 0
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Valor inválido! Use apenas números.",
                ephemeral=True
            )
            return
        
        # Validar
        if bonus_type != "disabled" and bonus_value <= 0:
            await inter.response.send_message(
                f"{emoji.wrong} Para ativar o bônus, informe um valor maior que 0.",
                ephemeral=True
            )
            return
        
        if bonus_type == "percentage" and bonus_value > 100:
            await inter.response.send_message(
                f"{emoji.wrong} Porcentagem máxima é 100%.",
                ephemeral=True
            )
            return
        
        # Salvar
        config = db.get_document("loja_saldo_config") or self.config
        config["bonus"] = {
            "type": bonus_type,
            "value": bonus_value
        }
        db.save_document("loja_saldo_config", config)
        
        # Atualizar painel
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        
        from .config_panel import panel_embed, panel_components
        if mode == "embed":
            panel_data = panel_embed(inter, config)
        else:
            panel_data = panel_components(inter, config)
        
        if "embed" in panel_data:
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
