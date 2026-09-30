import disnake
import re
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class StoreHoursPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return StoreHoursPreferences._panel_embed(inter) if mode == "embed" else StoreHoursPreferences._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        prefs = db.get_document("loja_preferences") or {}
        office_hours = prefs.get("office_hours", {})
        
        enabled = office_hours.get("enabled", False)
        start_time = office_hours.get("start_time", "")
        end_time = office_hours.get("end_time", "")
        off_days = office_hours.get("off_days", [])
        custom_message = office_hours.get("message", "")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        status_text = f"{emoji.on if enabled else emoji.off} **Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        if enabled:
            status_text += f"-# Horário: `{start_time}` às `{end_time}`\n"
            if off_days:
                status_text += f"-# Dias sem funcionamento: `{', '.join(off_days)}`\n"
            if custom_message:
                status_text += f"-# Mensagem personalizada configurada"
        else:
            status_text += "-# Configure o horário de abertura e fechamento para ativar"

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Preferências > **Horário de Funcionamento**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(status_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Configurar Horário",
                        emoji=emoji.edit,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Loja_Pref_StoreHours_Edit"
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
        office_hours = prefs.get("office_hours", {})
        
        enabled = office_hours.get("enabled", False)
        start_time = office_hours.get("start_time", "")
        end_time = office_hours.get("end_time", "")
        off_days = office_hours.get("off_days", [])
        custom_message = office_hours.get("message", "")

        status_text = f"{emoji.on if enabled else emoji.off} **Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        if enabled:
            status_text += f"-# Horário: `{start_time}` às `{end_time}`\n"
            if off_days:
                status_text += f"-# Dias sem funcionamento: `{', '.join(off_days)}`\n"
            if custom_message:
                status_text += f"-# Mensagem personalizada configurada"
        else:
            status_text += "-# Configure o horário de abertura e fechamento para ativar"

        embed = disnake.Embed(
            title="Horário de Funcionamento",
            description=(
                "-# Painel > Loja > Preferências > **Horário de Funcionamento**\n\n"
                f"{status_text}"
            )
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar Horário",
                    emoji=emoji.edit,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Loja_Pref_StoreHours_Edit"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Preferencias")
            )
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Pref_StoreHours_Edit":
            await inter.response.send_modal(StoreHoursModal())


class StoreHoursModal(disnake.ui.Modal):
    def __init__(self):
        prefs = db.get_document("loja_preferences") or {}
        office_hours = prefs.get("office_hours", {})

        components = [
            disnake.ui.TextInput(
                label="Horário de Abertura (ex: 09:00)",
                custom_id="start_time",
                value=office_hours.get("start_time"),
                max_length=5,
                required=False,
                placeholder="09:00"
            ),
            disnake.ui.TextInput(
                label="Horário de Fechamento (ex: 18:00)",
                custom_id="end_time",
                value=office_hours.get("end_time"),
                max_length=5,
                required=False,
                placeholder="18:00"
            ),
            disnake.ui.TextInput(
                label="Dias que não funcionará (ex: sab,dom)",
                custom_id="off_days",
                value=",".join(office_hours.get("off_days", [])),
                style=disnake.TextInputStyle.paragraph,
                required=False,
                placeholder="seg,ter,qua,qui,sex,sab,dom"
            ),
            disnake.ui.TextInput(
                label="Mensagem fora de horário",
                custom_id="message",
                value=office_hours.get("message"),
                style=disnake.TextInputStyle.paragraph,
                required=False,
                placeholder="Nosso horário de atendimento é das {start_time} às {end_time}."
            ),
        ]
        super().__init__(title="Configurar Horário de Funcionamento", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        start_time = inter.text_values.get("start_time")
        end_time = inter.text_values.get("end_time")
        off_days_str = inter.text_values.get("off_days", "")
        custom_message = inter.text_values.get("message")

        # Validações
        time_pattern = re.compile(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")

        if start_time and not time_pattern.match(start_time):
            return await inter.response.send_message(f"**Horário de Abertura Inválido!**\nUse o formato `HH:MM` (ex: `09:00`).", ephemeral=True)
        
        if end_time and not time_pattern.match(end_time):
            return await inter.response.send_message(f"**Horário de Fechamento Inválido!**\nUse o formato `HH:MM` (ex: `18:30`).", ephemeral=True)

        valid_days = {"seg", "ter", "qua", "qui", "sex", "sab", "dom"}
        user_days = {day.strip() for day in off_days_str.split(",") if day.strip()}
        invalid_days = user_days - valid_days

        if invalid_days:
            return await inter.response.send_message(f"**Dias Inválidos:** `{', '.join(invalid_days)}`\nUse apenas as abreviações: seg, ter, qua, qui, sex, sab, dom.", ephemeral=True)

        # Salvar dados
        prefs = db.get_document("loja_preferences") or {}
        if not isinstance(prefs, dict):
            prefs = {}
        
        if "office_hours" not in prefs:
            prefs["office_hours"] = {}

        enabled = bool(start_time and end_time)

        prefs["office_hours"]["enabled"] = enabled
        prefs["office_hours"]["start_time"] = start_time
        prefs["office_hours"]["end_time"] = end_time
        prefs["office_hours"]["off_days"] = sorted(list(user_days))
        prefs["office_hours"]["message"] = custom_message

        db.save_document("loja_preferences", prefs)
        
        mode = db.get_document("custom_mode").get("mode")
        panel = StoreHoursPreferences.panel(inter)
        if mode == "embed":
            await inter.response.edit_message(**panel)
        else:
            await inter.response.edit_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


def setup(bot: commands.Bot):
    bot.add_cog(StoreHoursPreferences(bot))
