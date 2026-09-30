import disnake
from . import helpers
from functions.database import database as db

class SettingModal(disnake.ui.Modal):
    def __init__(self, cog, original_inter: disnake.MessageInteraction, tipo: str, key: str, title: str, label: str, current_value: any):
        self.cog = cog
        self.original_inter = original_inter
        self.tipo = tipo
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
        config[self.tipo][self.key] = new_value
        helpers.salvar_config(config)

        await modal_inter.response.defer(with_message=False)
        await self.cog.display_panel(self.original_inter, tipo=self.tipo)

# --- Main Panel Handlers ---

async def handle_tipo_select(cog, inter: disnake.MessageInteraction):
    tipo = inter.values[0]
    await cog.display_panel(inter, tipo=tipo)

async def handle_advanced_select(cog, inter: disnake.MessageInteraction):
    action = inter.values[0]
    action_map = {
        "punicao": cog.display_punicao_panel,
        "cargo_imune": cog.display_cargo_imune_panel,
        "categoria_imune": cog.display_categoria_imune_panel,
        "canal_logs": cog.display_logs_panel,
    }
    if action in action_map:
        await action_map[action](inter)

# --- Sub-Panel (per-type) Handlers ---

async def handle_per_type_config(cog, inter: disnake.MessageInteraction, tipo: str):
    action = inter.values[0]
    config = helpers.carregar_config()

    if action == "toggle":
        config[tipo]["ativado"] = not config[tipo].get("ativado", False)
        helpers.salvar_config(config)
        await cog.display_panel(inter, tipo=tipo)
    elif action == "limite":
        modal = SettingModal(
            cog=cog, original_inter=inter, tipo=tipo, key="limite",
            title=f"Definir Limite ({tipo.capitalize()})",
            label="Novo Limite de Ações",
            current_value=config[tipo].get("limite", 0)
        )
        await inter.response.send_modal(modal)
    elif action == "intervalo":
        modal = SettingModal(
            cog=cog, original_inter=inter, tipo=tipo, key="intervalo",
            title=f"Definir Intervalo ({tipo.capitalize()})",
            label="Novo Intervalo (em segundos)",
            current_value=config[tipo].get("intervalo", 0)
        )
        await inter.response.send_modal(modal)

# --- Advanced Settings Handlers ---

async def handle_punicao_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["canais_avancado"]["punicao"] = inter.values[0]
    helpers.salvar_config(config)
    await cog.display_punicao_panel(inter)

async def handle_cargo_imune_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["canais_avancado"]["cargos_imunes"] = [int(r) for r in inter.values]
    helpers.salvar_config(config)
    await cog.display_cargo_imune_panel(inter)

async def handle_cargo_imune_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["canais_avancado"]["cargos_imunes"] = []
    helpers.salvar_config(config)
    await cog.display_cargo_imune_panel(inter)

async def handle_categoria_imune_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["canais_avancado"]["categorias_imunes"] = [int(c) for c in inter.values]
    helpers.salvar_config(config)
    await cog.display_categoria_imune_panel(inter)

async def handle_categoria_imune_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["canais_avancado"]["categorias_imunes"] = []
    helpers.salvar_config(config)
    await cog.display_categoria_imune_panel(inter)

async def handle_logs_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["canais_avancado"]["canal_logs"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_logs_panel(inter)

async def handle_logs_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["canais_avancado"]["canal_logs"] = None
    helpers.salvar_config(config)
    await cog.display_logs_panel(inter)

async def handle_logs_create(cog, inter: disnake.MessageInteraction):
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
            "logs-de-protecao-canais",
            category=category,
            overwrites=overwrites
        )
        config = helpers.carregar_config()
        config["canais_avancado"]["canal_logs"] = ch.id
        helpers.salvar_config(config)
    except disnake.Forbidden:
        await inter.followup.send("Não tenho permissão para criar o canal de logs.", ephemeral=True)
        return
    
    await cog.display_logs_panel(inter)
