import disnake
from . import helpers
from functions.database import database as db

async def handle_toggle(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    is_enabled = config[helpers.CHAVE].get("ativado", False)
    config[helpers.CHAVE]["ativado"] = not is_enabled
    helpers.salvar_config(config)
    await cog.display_panel(inter)

async def handle_set_punishment(cog, inter: disnake.MessageInteraction):
    await cog.display_punishment_panel(inter)

async def handle_set_immune_role(cog, inter: disnake.MessageInteraction):
    await cog.display_immune_role_panel(inter)

async def handle_set_log_channel(cog, inter: disnake.MessageInteraction):
    await cog.display_log_channel_panel(inter)

async def handle_punishment_select(cog, inter: disnake.MessageInteraction):
    value = inter.values[0]
    config = helpers.carregar_config()
    config["privatizacao_urls_avancado"]["punicao"] = value
    helpers.salvar_config(config)
    await cog.display_punishment_panel(inter)

async def handle_immune_role_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["privatizacao_urls_avancado"]["cargos_imunes"] = [int(role_id) for role_id in inter.values] if inter.values else []
    helpers.salvar_config(config)
    await cog.display_immune_role_panel(inter)

async def handle_log_channel_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["privatizacao_urls_avancado"]["canal_logs"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)

async def handle_immune_role_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["privatizacao_urls_avancado"]["cargos_imunes"] = []
    helpers.salvar_config(config)
    await cog.display_immune_role_panel(inter)

async def handle_log_channel_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["privatizacao_urls_avancado"]["canal_logs"] = None
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)

async def handle_log_channel_create(cog, inter: disnake.MessageInteraction):
    await inter.response.defer()
    
    category = disnake.utils.get(inter.guild.categories, name="Logs")
    if category is None:
        try:
            category = await inter.guild.create_category("Logs")
        except disnake.Forbidden:
            await inter.followup.send("Não tenho permissão para criar categorias.", ephemeral=True)
            return

    try:
        overwrites = {
            inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False)
        }
        ch = await inter.guild.create_text_channel(
            "logs-de-privatizacao-urls",
            category=category,
            overwrites=overwrites
        )
        config = helpers.carregar_config()
        config["privatizacao_urls_avancado"]["canal_logs"] = ch.id
        helpers.salvar_config(config)
    except disnake.Forbidden:
        await inter.followup.send("Não tenho permissão para criar o canal de logs.", ephemeral=True)
        return
    
    await cog.display_log_channel_panel(inter)
