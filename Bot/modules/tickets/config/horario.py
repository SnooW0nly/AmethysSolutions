import disnake
import re
from functions.database import database as db
from .edit_panel import SpecificPanelView_components, SpecificPanelView_embed

class OfficeHoursModal(disnake.ui.Modal):
    def __init__(self, panel_id: str):
        self.panel_id = panel_id
        
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id, {})
        office_hours_data = panel_data.get("office_hours", {})

        components = [
            disnake.ui.TextInput(
                label="Horário de Abertura (ex: 09:00)",
                custom_id="start_time",
                value=office_hours_data.get("start_time"),
                max_length=5,
                required=False,
                placeholder="09:00"
            ),
            disnake.ui.TextInput(
                label="Horário de Fechamento (ex: 18:00)",
                custom_id="end_time",
                value=office_hours_data.get("end_time"),
                max_length=5,
                required=False,
                placeholder="18:00"
            ),
            disnake.ui.TextInput(
                label="Dias que não funcionará (ex: sab,dom)",
                custom_id="off_days",
                value=",".join(office_hours_data.get("off_days", [])),
                style=disnake.TextInputStyle.paragraph,
                required=False,
                placeholder="seg,ter,qua,qui,sex,sab,dom"
            ),
             disnake.ui.TextInput(
                label="Mensagem fora de horário",
                custom_id="message",
                value=office_hours_data.get("message"),
                style=disnake.TextInputStyle.paragraph,
                required=False,
                placeholder="Nosso horário de atendimento é das {start_time} às {end_time} nos dias úteis."
            ),
        ]
        super().__init__(title="Configurar Horário de Atendimento", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        start_time = inter.text_values.get("start_time")
        end_time = inter.text_values.get("end_time")
        off_days_str = inter.text_values.get("off_days", "")
        message = inter.text_values.get("message")

        # --- Validações ---
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

        # --- Salvar Dados ---
        config = db.get_document("tickets_config") or {}
        
        if self.panel_id not in config.get("panels", {}):
            return await inter.response.send_message("Painel não encontrado. A configuração não pôde ser salva.", ephemeral=True)

        if "office_hours" not in config["panels"][self.panel_id]:
            config["panels"][self.panel_id]["office_hours"] = {}

        enabled = bool(start_time and end_time)

        config["panels"][self.panel_id]["office_hours"]["enabled"] = enabled
        config["panels"][self.panel_id]["office_hours"]["start_time"] = start_time
        config["panels"][self.panel_id]["office_hours"]["end_time"] = end_time
        config["panels"][self.panel_id]["office_hours"]["off_days"] = sorted(list(user_days))
        config["panels"][self.panel_id]["office_hours"]["message"] = message

        db.save_document("tickets_config", config)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=SpecificPanelView_components(inter, self.panel_id))
        else:
            embed, components = SpecificPanelView_embed(inter, self.panel_id)
            await inter.response.edit_message(embed=embed, components=components)
