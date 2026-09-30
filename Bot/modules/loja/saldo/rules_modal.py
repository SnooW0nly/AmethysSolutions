"""
Modal para configurar regras do sistema de saldo
"""
import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class RulesModal(disnake.ui.Modal):
    """Modal para configurar as regras de uso do saldo"""
    
    def __init__(self, config: dict):
        self.config = config
        rules = config.get("rules", {})
        deposit_settings = config.get("deposit_settings", {})
        
        max_pct = rules.get("max_usage_percentage", 100)
        max_amt = rules.get("max_usage_amount")
        min_amt = rules.get("min_usage_amount", 0)
        
        min_deposit = deposit_settings.get("min_deposit", 5.00)
        max_deposit = deposit_settings.get("max_deposit", 1000.00)
        
        components = [
            disnake.ui.TextInput(
                label="Porcentagem Máxima de Uso (%)",
                placeholder="Ex: 50 (para 50% do valor)",
                custom_id="max_percentage",
                style=disnake.TextInputStyle.short,
                value=str(max_pct) if max_pct else "100",
                required=True,
                max_length=5
            ),
            disnake.ui.TextInput(
                label="Valor Máximo de Uso (R$)",
                placeholder="Deixe vazio para sem limite",
                custom_id="max_amount",
                style=disnake.TextInputStyle.short,
                value=str(max_amt) if max_amt else "",
                required=False,
                max_length=10
            ),
            disnake.ui.TextInput(
                label="Valor Mínimo de Uso (R$)",
                placeholder="Ex: 5.00",
                custom_id="min_amount",
                style=disnake.TextInputStyle.short,
                value=str(min_amt) if min_amt else "0",
                required=False,
                max_length=10
            ),
            disnake.ui.TextInput(
                label="Depósito Mínimo/Máximo (R$)",
                placeholder="Ex: 5.00,1000.00",
                custom_id="deposit_range",
                style=disnake.TextInputStyle.short,
                value=f"{min_deposit:.2f},{max_deposit:.2f}",
                required=True,
                max_length=25
            ),
        ]
        
        super().__init__(title="Configurar Regras de Saldo", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        try:
            # Processar porcentagem máxima
            max_pct_input = inter.text_values.get("max_percentage", "100").strip()
            max_pct = int(max_pct_input) if max_pct_input else 100
            if max_pct < 1 or max_pct > 100:
                raise ValueError("Porcentagem deve ser entre 1 e 100")
            
            # Processar valor máximo
            max_amt_input = inter.text_values.get("max_amount", "").strip()
            max_amt = float(max_amt_input.replace(",", ".")) if max_amt_input else None
            
            # Processar valor mínimo
            min_amt_input = inter.text_values.get("min_amount", "0").strip()
            min_amt = float(min_amt_input.replace(",", ".")) if min_amt_input else 0
            
            # Processar faixa de depósito
            deposit_input = inter.text_values.get("deposit_range", "5.00,1000.00").strip()
            parts = deposit_input.replace(" ", "").split(",")
            if len(parts) != 2:
                raise ValueError("Faixa de depósito deve ser: mínimo,máximo")
            
            min_deposit = float(parts[0].replace(",", "."))
            max_deposit = float(parts[1].replace(",", "."))
            
            if min_deposit < 0:
                raise ValueError("Depósito mínimo não pode ser negativo")
            if max_deposit <= min_deposit:
                raise ValueError("Depósito máximo deve ser maior que o mínimo")
            
        except ValueError as e:
            await inter.response.send_message(
                f"{emoji.wrong} Erro: {str(e)}",
                ephemeral=True
            )
            return
        
        # Salvar
        config = db.get_document("loja_saldo_config") or self.config
        config["rules"] = {
            "max_usage_percentage": max_pct,
            "max_usage_amount": max_amt,
            "min_usage_amount": min_amt,
            "allow_partial_payment": True  # Sempre permitir parcial
        }
        config["deposit_settings"]["min_deposit"] = min_deposit
        config["deposit_settings"]["max_deposit"] = max_deposit
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
