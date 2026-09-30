"""
Sistema de manutenção da loja
Quando ativado, bloqueia todas as compras exceto para admins (se configurado)
"""

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class MaintenancePreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return MaintenancePreferences._panel_embed(inter) if mode == "embed" else MaintenancePreferences._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        maintenance = db.get_document("loja_maintenance") or {}
        
        enabled = maintenance.get("enabled", False)
        custom_message = maintenance.get("message", "")
        allow_admins = maintenance.get("allow_admins", True)

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        status_text = f"{emoji.on if enabled else emoji.off} **Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        if enabled:
            if custom_message:
                status_text += f"-# Mensagem: `{custom_message[:50]}...`\n"
            else:
                status_text += f"-# Mensagem padrão configurada\n"
            status_text += f"-# Admins podem comprar: {'Sim' if allow_admins else 'Não'}\n"
        else:
            status_text += "-# A loja está funcionando normalmente"

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Preferências > **Manutenção**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(status_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar" if not enabled else "Desativar",
                        emoji=emoji.power,
                        style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                        custom_id="Loja_Pref_Maintenance_Toggle"
                    ),
                    disnake.ui.Button(
                        label="Configurar Mensagem",
                        emoji=emoji.edit,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Loja_Pref_Maintenance_Edit"
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Permitir Admins" if not allow_admins else "Bloquear Admins",
                        emoji=emoji.members if allow_admins else emoji.off,
                        style=disnake.ButtonStyle.grey,
                        custom_id="Loja_Pref_Maintenance_Admins"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Preferencias")
            )
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        maintenance = db.get_document("loja_maintenance") or {}
        
        enabled = maintenance.get("enabled", False)
        custom_message = maintenance.get("message", "")
        allow_admins = maintenance.get("allow_admins", True)

        status_text = f"**Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        if enabled:
            if custom_message:
                status_text += f"-# Mensagem: `{custom_message[:50]}...`\n"
            else:
                status_text += f"-# Mensagem padrão configurada\n"
            status_text += f"-# Admins podem comprar: {'Sim' if allow_admins else 'Não'}\n"
        else:
            status_text += "-# A loja está funcionando normalmente"

        embed = disnake.Embed(
            title="Manutenção da Loja",
            description=(
                "-# Painel > Loja > Preferências > **Manutenção**\n\n"
                f"{status_text}"
            )
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ativar" if not enabled else "Desativar",
                    emoji=emoji.power,
                    style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                    custom_id="Loja_Pref_Maintenance_Toggle"
                ),
                disnake.ui.Button(
                    label="Configurar Mensagem",
                    emoji=emoji.edit,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Loja_Pref_Maintenance_Edit"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Permitir Admins" if not allow_admins else "Bloquear Admins",
                    emoji=emoji.members if allow_admins else emoji.off,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Loja_Pref_Maintenance_Admins"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Preferencias")
            )
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Pref_Maintenance_Toggle":
            maintenance = db.get_document("loja_maintenance") or {}
            if not isinstance(maintenance, dict):
                maintenance = {}
            
            current = maintenance.get("enabled", False)
            maintenance["enabled"] = not current
            
            # Se ativando pela primeira vez e não tem mensagem, usar padrão
            if maintenance["enabled"] and not maintenance.get("message"):
                maintenance["message"] = "Olá, {user} a loja está em manutenção, tente novamente mais tarde."
            
            db.save_document("loja_maintenance", maintenance)
            
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = MaintenancePreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_Pref_Maintenance_Edit":
            maintenance = db.get_document("loja_maintenance") or {}
            current_message = maintenance.get("message", "Olá, {user} a loja está em manutenção, tente novamente mais tarde.")
            await inter.response.send_modal(MaintenanceMessageModal(current_message))
        
        elif inter.component.custom_id == "Loja_Pref_Maintenance_Admins":
            maintenance = db.get_document("loja_maintenance") or {}
            if not isinstance(maintenance, dict):
                maintenance = {}
            
            current = maintenance.get("allow_admins", True)
            maintenance["allow_admins"] = not current
            db.save_document("loja_maintenance", maintenance)
            
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = MaintenancePreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


class MaintenanceMessageModal(disnake.ui.Modal):
    def __init__(self, current_message: str = ""):
        components = [
            disnake.ui.TextInput(
                label="Mensagem de Manutenção",
                custom_id="message",
                value=current_message,
                style=disnake.TextInputStyle.paragraph,
                required=True,
                placeholder="Olá, {user} a loja está em manutenção, tente novamente mais tarde.",
                max_length=500
            )
        ]
        super().__init__(title="Configurar Mensagem de Manutenção", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        message_text = inter.text_values.get("message", "").strip()
        
        if not message_text:
            await inter.response.send_message(
                f"{emoji.wrong} A mensagem não pode estar vazia!",
                ephemeral=True
            )
            return
        
        maintenance = db.get_document("loja_maintenance") or {}
        if not isinstance(maintenance, dict):
            maintenance = {}
        
        maintenance["message"] = message_text
        db.save_document("loja_maintenance", maintenance)
        
        mode = db.get_document("custom_mode").get("mode")
        panel = MaintenancePreferences.panel(inter)
        if mode == "embed":
            await inter.response.edit_message(**panel)
        else:
            await inter.response.edit_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


def setup(bot: commands.Bot):
    bot.add_cog(MaintenancePreferences(bot))
