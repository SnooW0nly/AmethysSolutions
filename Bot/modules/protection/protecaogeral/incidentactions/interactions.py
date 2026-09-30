import datetime
import aiohttp
import disnake

from . import helpers
from functions.database import database as db
from functions.emoji import emoji

DISCORD_API_BASE = "https://discord.com/api/v10"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

async def _aplicar_incident_actions(
    guild: disnake.Guild,
    dms_minutos: int | None,
    invites_minutos: int | None,
    bot_token: str,
) -> tuple[bool, str, dict]:
    """
    Aplica ou limpa incident actions via API do Discord.

    - Passar None em dms_minutos / invites_minutos limpa a ação (desativa).
    - Retorna (sucesso, mensagem, payload_resposta).
    """
    payload = {}

    if dms_minutos is not None:
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=dms_minutos)
        payload["dms_disabled_until"] = until.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        payload["dms_disabled_until"] = None

    if invites_minutos is not None:
        until = datetime.datetime.utcnow() + datetime.timedelta(minutes=invites_minutos)
        payload["invites_disabled_until"] = until.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    else:
        payload["invites_disabled_until"] = None

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"{DISCORD_API_BASE}/guilds/{guild.id}/incident-actions",
            headers=headers,
            json=payload,
        ) as resp:
            if resp.status == 200:
                return True, "Aplicado com sucesso.", await resp.json()
            else:
                texto = await resp.text()
                return False, f"Erro {resp.status}: {texto}", {}


def _get_bot_token() -> str:
    """Lê o token do bot do config.json."""
    try:
        import json
        with open("config.json", "r") as f:
            data = json.load(f)
        return data["bot"]["token"]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Handlers de dropdowns / botões
# ---------------------------------------------------------------------------

async def handle_toggle_dms(cog, inter: disnake.MessageInteraction):
    """Ativa ou desativa DMs desabilitadas."""
    config = helpers.carregar_config()
    dados = config[helpers.CHAVE]
    novo_estado = not dados.get("dms_ativado", False)
    dados["dms_ativado"] = novo_estado
    helpers.salvar_config(config)

    if novo_estado:
        # Aplicar via API
        minutos = helpers.duracao_para_minutos(dados.get("duracao_dms", "1h"))
        token = _get_bot_token()
        ok, msg, _ = await _aplicar_incident_actions(inter.guild, minutos, None, token)
        if not ok:
            dados["dms_ativado"] = False
            helpers.salvar_config(config)
            await inter.response.send_message(f"{emoji.wrong} Falha ao ativar bloqueio de DMs: {msg}", ephemeral=True)
            return
    else:
        # Limpar via API
        token = _get_bot_token()
        await _aplicar_incident_actions(inter.guild, None, None, token)

    await cog.display_panel(inter)


async def handle_toggle_invites(cog, inter: disnake.MessageInteraction):
    """Ativa ou desativa Invites desabilitados."""
    config = helpers.carregar_config()
    dados = config[helpers.CHAVE]
    novo_estado = not dados.get("invites_ativado", False)
    dados["invites_ativado"] = novo_estado
    helpers.salvar_config(config)

    if novo_estado:
        minutos = helpers.duracao_para_minutos(dados.get("duracao_invites", "1h"))
        token = _get_bot_token()
        ok, msg, _ = await _aplicar_incident_actions(inter.guild, None, minutos, token)
        if not ok:
            dados["invites_ativado"] = False
            helpers.salvar_config(config)
            await inter.response.send_message(f"{emoji.wrong} Falha ao ativar bloqueio de Invites: {msg}", ephemeral=True)
            return
    else:
        token = _get_bot_token()
        await _aplicar_incident_actions(inter.guild, None, None, token)

    await cog.display_panel(inter)


async def handle_duracao_dms_select(cog, inter: disnake.MessageInteraction):
    """Salva a duração escolhida para DMs e reaplicar se estiver ativo."""
    valor = inter.values[0]
    config = helpers.carregar_config()
    config[helpers.CHAVE]["duracao_dms"] = valor
    helpers.salvar_config(config)

    # Se já estiver ativo, reaplicar com nova duração
    if config[helpers.CHAVE].get("dms_ativado", False):
        minutos = helpers.duracao_para_minutos(valor)
        token = _get_bot_token()
        await _aplicar_incident_actions(inter.guild, minutos, None, token)

    await cog.display_panel(inter)


async def handle_duracao_invites_select(cog, inter: disnake.MessageInteraction):
    """Salva a duração escolhida para Invites e reaplicar se estiver ativo."""
    valor = inter.values[0]
    config = helpers.carregar_config()
    config[helpers.CHAVE]["duracao_invites"] = valor
    helpers.salvar_config(config)

    if config[helpers.CHAVE].get("invites_ativado", False):
        minutos = helpers.duracao_para_minutos(valor)
        token = _get_bot_token()
        await _aplicar_incident_actions(inter.guild, None, minutos, token)

    await cog.display_panel(inter)


async def handle_log_channel_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config[f"{helpers.CHAVE}_avancado"]["canal_logs"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)


async def handle_set_log_channel_nav(cog, inter: disnake.MessageInteraction):
    """Navega para o painel de canal de logs."""
    await cog.display_log_channel_panel(inter)


async def handle_log_channel_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config[f"{helpers.CHAVE}_avancado"]["canal_logs"] = None
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)


async def handle_log_channel_create(cog, inter: disnake.MessageInteraction):
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
            "logs-incident-actions",
            category=category,
            overwrites=overwrites,
        )
        config = helpers.carregar_config()
        config[f"{helpers.CHAVE}_avancado"]["canal_logs"] = ch.id
        helpers.salvar_config(config)
    except disnake.Forbidden:
        await inter.followup.send("Não tenho permissão para criar canais.", ephemeral=True)
        return

    await cog.display_log_channel_panel(inter)