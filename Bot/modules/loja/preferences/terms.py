"""
Sistema de termos da loja
Usuários precisam aceitar os termos antes de prosseguir com o pagamento
"""

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class TermsPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return TermsPreferences._panel_embed(inter) if mode == "embed" else TermsPreferences._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        prefs = db.get_document("loja_preferences") or {}
        terms = prefs.get("terms", {})
        
        enabled = terms.get("enabled", False)
        terms_text = terms.get("text", "")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        status_text = f"{emoji.on if enabled else emoji.off} **Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        if enabled:
            if terms_text:
                preview = terms_text[:100] + "..." if len(terms_text) > 100 else terms_text
                status_text += f"-# Termos configurados: `{preview}`\n"
            else:
                status_text += f"-# Termos: `Não configurado`\n"
        else:
            status_text += "-# Configure os termos e ative para exigir aceitação"

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Preferências > **Termos da Loja**"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar" if not enabled else "Desativar",
                        emoji=emoji.power,
                        style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                        custom_id="Loja_Pref_Terms_Toggle"
                    ),
                    disnake.ui.Button(
                        label="Configurar Termos",
                        emoji=emoji.edit,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Loja_Pref_Terms_Edit"
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
        prefs = db.get_document("loja_preferences") or {}
        terms = prefs.get("terms", {})
        
        enabled = terms.get("enabled", False)
        terms_text = terms.get("text", "")

        status_text = f"{emoji.on if enabled else emoji.off} **Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        if enabled:
            if terms_text:
                preview = terms_text[:100] + "..." if len(terms_text) > 100 else terms_text
                status_text += f"-# Termos configurados: `{preview}`\n"
            else:
                status_text += f"-# Termos: `Não configurado`\n"
        else:
            status_text += "-# Configure os termos e ative para exigir aceitação"

        embed = disnake.Embed(
            title="Termos da Loja",
            description=(
                "-# Painel > Loja > Preferências > **Termos da Loja**"
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
                    custom_id="Loja_Pref_Terms_Toggle"
                ),
                disnake.ui.Button(
                    label="Configurar Termos",
                    emoji=emoji.edit,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Loja_Pref_Terms_Edit"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Preferencias")
            )
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Pref_Terms_Toggle":
            prefs = db.get_document("loja_preferences") or {}
            if not isinstance(prefs, dict):
                prefs = {}
            
            if "terms" not in prefs:
                prefs["terms"] = {}
            
            current = prefs["terms"].get("enabled", False)
            prefs["terms"]["enabled"] = not current
            db.save_document("loja_preferences", prefs)
            
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = TermsPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_Pref_Terms_Edit":
            prefs = db.get_document("loja_preferences") or {}
            terms = prefs.get("terms", {})
            current_text = terms.get("text", "")
            await inter.response.send_modal(TermsEditModal(current_text))


class TermsEditModal(disnake.ui.Modal):
    def __init__(self, current_text: str = ""):
        components = [
            disnake.ui.TextInput(
                label="Termos da Loja",
                custom_id="terms_text",
                value=current_text,
                style=disnake.TextInputStyle.paragraph,
                required=True,
                placeholder="Digite os termos que os usuários precisam aceitar antes de comprar...",
                max_length=2000
            )
        ]
        super().__init__(title="Configurar Termos da Loja", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        terms_text = inter.text_values.get("terms_text", "").strip()
        
        if not terms_text:
            await inter.response.send_message(
                f"{emoji.wrong} Os termos não podem estar vazios!",
                ephemeral=True
            )
            return
        
        prefs = db.get_document("loja_preferences") or {}
        if not isinstance(prefs, dict):
            prefs = {}
        
        if "terms" not in prefs:
            prefs["terms"] = {}
        
        prefs["terms"]["text"] = terms_text
        db.save_document("loja_preferences", prefs)
        
        mode = db.get_document("custom_mode").get("mode")
        panel = TermsPreferences.panel(inter)
        if mode == "embed":
            await inter.response.edit_message(**panel)
        else:
            await inter.response.edit_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


def setup(bot: commands.Bot):
    bot.add_cog(TermsPreferences(bot))
