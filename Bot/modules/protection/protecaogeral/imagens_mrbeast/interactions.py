import disnake

from . import helpers
from functions.emoji import emoji


# ---------------------------------------------------------------------------
# Handlers de ações do painel principal
# ---------------------------------------------------------------------------

async def handle_toggle_ativado(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    dados = config[helpers.CHAVE]
    dados["ativado"] = not dados.get("ativado", False)
    helpers.salvar_config(config)
    await cog.display_panel(inter)


async def handle_punicao_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config[f"{helpers.CHAVE}_avancado"]["punicao"] = inter.values[0]
    helpers.salvar_config(config)
    await cog.display_panel(inter)


async def handle_limite_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config[f"{helpers.CHAVE}_avancado"]["limite"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_panel(inter)


async def handle_intervalo_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config[f"{helpers.CHAVE}_avancado"]["intervalo"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_panel(inter)


# ---------------------------------------------------------------------------
# Handlers do painel de cargos imunes
# ---------------------------------------------------------------------------

async def handle_nav_cargos_imunes(cog, inter: disnake.MessageInteraction):
    await cog.display_cargos_imunes_panel(inter)


async def handle_cargos_imunes_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    avancado = config[f"{helpers.CHAVE}_avancado"]
    atual = set(avancado.get("cargos_imunes", []))
    selecionados = {int(v) for v in inter.values}
    # Toggle: se todos já estão, remove; senão adiciona
    if selecionados.issubset(atual):
        atual -= selecionados
    else:
        atual |= selecionados
    avancado["cargos_imunes"] = list(atual)
    helpers.salvar_config(config)
    await cog.display_cargos_imunes_panel(inter)


async def handle_cargos_imunes_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config[f"{helpers.CHAVE}_avancado"]["cargos_imunes"] = []
    helpers.salvar_config(config)
    await cog.display_cargos_imunes_panel(inter)


# ---------------------------------------------------------------------------
# Handlers do painel de canal de logs
# ---------------------------------------------------------------------------

async def handle_nav_canal_logs(cog, inter: disnake.MessageInteraction):
    await cog.display_canal_logs_panel(inter)


async def handle_canal_logs_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config[f"{helpers.CHAVE}_avancado"]["canal_logs"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_canal_logs_panel(inter)


async def handle_canal_logs_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config[f"{helpers.CHAVE}_avancado"]["canal_logs"] = None
    helpers.salvar_config(config)
    await cog.display_canal_logs_panel(inter)


async def handle_canal_logs_create(cog, inter: disnake.MessageInteraction):
    await inter.response.defer()

    category = disnake.utils.get(inter.guild.categories, name="Logs")
    if not category:
        try:
            overwrites = {inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False)}
            category = await inter.guild.create_category("Logs", overwrites=overwrites)
        except disnake.Forbidden:
            await inter.followup.send("Não tenho permissão para criar categorias.", ephemeral=True)
            return

    try:
        overwrites = {inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False)}
        ch = await inter.guild.create_text_channel(
            "logs-mrbeast",
            category=category,
            overwrites=overwrites,
        )
        config = helpers.carregar_config()
        config[f"{helpers.CHAVE}_avancado"]["canal_logs"] = ch.id
        helpers.salvar_config(config)
    except disnake.Forbidden:
        await inter.followup.send("Não tenho permissão para criar canais.", ephemeral=True)
        return

    await cog.display_canal_logs_panel(inter)
