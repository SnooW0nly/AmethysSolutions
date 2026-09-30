import disnake
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

    async def _update_panel(self):
        panel_message = await self.original_inter.original_message()
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed, components = self.cog.PainelEmbed(self.original_inter)
            await panel_message.edit(content=None, embed=embed, components=components)
        else:
            components = self.cog.PainelComponents(self.original_inter)
            await panel_message.edit(content=None, embed=None, components=components)

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
        await self._update_panel()

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
        title="Definir Limite", label="Novo Limite de Expulsões",
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

async def handle_set_immune_role(cog, inter: disnake.MessageInteraction):
    await cog.display_immune_role_panel(inter)

async def handle_set_log_channel(cog, inter: disnake.MessageInteraction):
    await cog.display_log_channel_panel(inter)

async def handle_punishment_select(cog, inter: disnake.MessageInteraction):
    value = inter.values[0]
    config = helpers.carregar_config()
    config["expulsoes_avancado"]["punicao"] = value
    helpers.salvar_config(config)
    await cog.display_punishment_panel(inter)

async def handle_immune_role_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["expulsoes_avancado"]["cargos_imunes"] = [int(role_id) for role_id in inter.values] if inter.values else []
    helpers.salvar_config(config)
    await cog.display_immune_role_panel(inter)

async def handle_log_channel_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["expulsoes_avancado"]["canal_logs"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)

async def handle_immune_role_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["expulsoes_avancado"]["cargos_imunes"] = []
    helpers.salvar_config(config)
    await cog.display_immune_role_panel(inter)

async def handle_log_channel_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["expulsoes_avancado"]["canal_logs"] = None
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)

async def handle_log_channel_create(cog, inter: disnake.MessageInteraction):
    await inter.response.defer()
    
    category = disnake.utils.get(inter.guild.categories, name="Logs")
    if category is None:
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
            "logs-de-protecao-expulsoes",
            category=category,
            overwrites=overwrites
        )
        config = helpers.carregar_config()
        config["expulsoes_avancado"]["canal_logs"] = ch.id
        helpers.salvar_config(config)
    except disnake.Forbidden:
        await inter.followup.send("Não tenho permissão para criar o canal de logs.", ephemeral=True)
        return
    
    await cog.display_log_channel_panel(inter)
