import disnake
import re
from . import helpers
from functions.database import database as db

class SettingModal(disnake.ui.Modal):
    def __init__(self, cog, original_inter: disnake.MessageInteraction, key: str, title: str, label: str, current_value: any):
        self.cog = cog
        self.original_inter = original_inter
        self.key = key
        
        components = [
            disnake.ui.TextInput(
                label=label,
                placeholder=f"Valor atual: {current_value}",
                custom_id="new_value",
                style=disnake.TextInputStyle.short,
                max_length=5,
            )
        ]
        super().__init__(title=title, components=components)

    async def callback(self, modal_inter: disnake.ModalInteraction):
        new_value_str = modal_inter.text_values["new_value"]
        try:
            new_value = int(new_value_str)
            if not (1 <= new_value <= 10000):
                await modal_inter.response.send_message("O valor deve ser um número inteiro entre 1 e 10000.", ephemeral=True)
                return
        except ValueError:
            await modal_inter.response.send_message("Por favor, insira um número inteiro válido.", ephemeral=True)
            return

        config = helpers.carregar_config()
        config[helpers.CHAVE][self.key] = new_value
        helpers.salvar_config(config)

        await modal_inter.response.defer(with_message=False)
        await self.cog.display_panel(self.original_inter)

class BotsPermitidosModal(disnake.ui.Modal):
    def __init__(self, cog, original_inter: disnake.MessageInteraction):
        self.cog = cog
        self.original_inter = original_inter
        
        config = helpers.carregar_config()
        bots_atuais = config.get("comandosext_avancado", {}).get("bots_permitidos", [])
        bots_str = ", ".join(map(str, bots_atuais))

        components = [
            disnake.ui.TextInput(
                label="IDs dos Bots Permitidos",
                placeholder="Insira os IDs separados por vírgula ou espaço",
                custom_id="bot_ids",
                style=disnake.TextInputStyle.paragraph,
                value=bots_str,
                required=False
            )
        ]
        super().__init__(title="Configurar Bots Permitidos", components=components)

    async def callback(self, modal_inter: disnake.ModalInteraction):
        bot_ids_str = modal_inter.text_values["bot_ids"]
        
        try:
            # Use regex to find all numbers and convert them to int
            bot_ids = [int(id_str) for id_str in re.findall(r'\d+', bot_ids_str)]
        except ValueError:
            await modal_inter.response.send_message("Por favor, insira apenas IDs numéricos válidos.", ephemeral=True)
            return

        config = helpers.carregar_config()
        config["comandosext_avancado"]["bots_permitidos"] = bot_ids
        helpers.salvar_config(config)

        await modal_inter.response.defer(with_message=False)
        await self.cog.display_panel(self.original_inter)

async def handle_toggle(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    is_enabled = config[helpers.CHAVE].get("ativado", False)
    config[helpers.CHAVE]["ativado"] = not is_enabled
    helpers.salvar_config(config)
    await cog.display_panel(inter)

async def handle_set_limit(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    current_limit = config[helpers.CHAVE].get("limite", 0)
    modal = SettingModal(
        cog=cog, original_inter=inter, key="limite",
        title="Definir Limite", label="Novo Limite de Comandos",
        current_value=current_limit
    )
    await inter.response.send_modal(modal)

async def handle_set_interval(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    current_interval = config[helpers.CHAVE].get("intervalo", 0)
    modal = SettingModal(
        cog=cog, original_inter=inter, key="intervalo",
        title="Definir Intervalo", label="Novo Intervalo (em segundos)",
        current_value=current_interval
    )
    await inter.response.send_modal(modal)

async def handle_set_punishment(cog, inter: disnake.MessageInteraction):
    await cog.display_punishment_panel(inter)

async def handle_set_allowed_bots(cog, inter: disnake.MessageInteraction):
    modal = BotsPermitidosModal(cog=cog, original_inter=inter)
    await inter.response.send_modal(modal)

async def handle_set_log_channel(cog, inter: disnake.MessageInteraction):
    await cog.display_log_channel_panel(inter)

async def handle_punishment_select(cog, inter: disnake.MessageInteraction):
    value = inter.values[0]
    config = helpers.carregar_config()
    config["comandosext_avancado"]["punicao"] = value
    helpers.salvar_config(config)
    await cog.display_punishment_panel(inter)

async def handle_log_channel_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["comandosext_avancado"]["canal_logs"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)

async def handle_log_channel_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["comandosext_avancado"]["canal_logs"] = None
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)

async def handle_log_channel_create(cog, inter: disnake.MessageInteraction):
    await inter.response.defer()
    
    category = disnake.utils.get(inter.guild.categories, name="Logs")
    if not category:
        try:
            overwrites = {
                inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False)
            }
            category = await inter.guild.create_category("Logs", overwrites=overwrites)
        except disnake.Forbidden:
            await inter.followup.send("Não tenho permissão para criar categorias.", ephemeral=True)
            return

    try:
        overwrites = {
            inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False)
        }
        ch = await inter.guild.create_text_channel(
            "logs-de-protecao-comandos-externos",
            category=category,
            overwrites=overwrites
        )
        config = helpers.carregar_config()
        config["comandosext_avancado"]["canal_logs"] = ch.id
        helpers.salvar_config(config)
    except disnake.Forbidden:
        await inter.followup.send("Não tenho permissão para criar o canal de logs.", ephemeral=True)
        return
    
    await cog.display_log_channel_panel(inter)
