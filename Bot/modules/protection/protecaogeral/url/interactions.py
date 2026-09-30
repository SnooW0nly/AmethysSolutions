import disnake
import datetime
from . import helpers, url_manager
from functions.database import database as db
from functions.emoji import emoji

class UrlConfigureModal(disnake.ui.Modal):
    def __init__(self, cog, original_inter: disnake.MessageInteraction):
        self.cog = cog
        self.original_inter = original_inter
        components = [
            disnake.ui.TextInput(
                label="Nome da URL",
                placeholder="Exemplo: amethys (resultará em discord.gg/amethys)",
                custom_id="url_name",
                style=disnake.TextInputStyle.short,
                max_length=32, min_length=3,
            )
        ]
        super().__init__(title="Configurar URL do Servidor", components=components)

    async def callback(self, modal_inter: disnake.ModalInteraction):
        url_name = modal_inter.text_values["url_name"].strip().lower()
        import re
        url_name = re.sub(r'[^a-z0-9-]', '', url_name)
        if not url_name:
            await modal_inter.response.send_message("Nome de URL inválido.", ephemeral=True)
            return

        config = helpers.carregar_config()
        avancado = config.get("protecao_url_avancado", {})
        token_user_id = avancado.get("token_user_id")
        if not token_user_id:
            await modal_inter.response.send_message(
                f"{emoji.warn} Configure uma conta primeiro em 'Configurações Avançadas -> Conta'.",
                ephemeral=True
            )
            return

        tokens = db.get_document("tokens", {}).get("list", [])
        token_data = next((t for t in tokens if t["user_id"] == token_user_id), None)
        if not token_data:
            await modal_inter.response.send_message(f"{emoji.warn} Conta não encontrada. Reconfigure.", ephemeral=True)
            return

        await modal_inter.response.defer()
        mgr = url_manager.URLManager(self.cog.bot)
        success, message = await mgr.set_vanity_url(
            modal_inter.guild.id,
            token_data["token"],
            token_data.get("password", ""),
            url_name
        )

        if success:
            avancado["url_nome"] = url_name
            config["protecao_url_avancado"] = avancado
            helpers.salvar_config(config)

            if avancado.get("canal_logs"):
                from modules.protection.tasks._common import enviar_log
                await enviar_log(
                    modal_inter.guild,
                    avancado["canal_logs"],
                    "Proteção URL - Configuração",
                    [
                        f"{emoji.check} **URL configurada com sucesso!**",
                        f"{emoji.link} discord.gg/{url_name}",
                        f"{emoji.members} **Por:** {modal_inter.author.mention}",
                        f"{emoji.members} **Conta:** {token_data['username']}"
                    ]
                )
            await modal_inter.followup.send(f"{emoji.check} URL configurada: discord.gg/{url_name}")
            await self.cog.display_panel(modal_inter)  # atualiza painel principal
        else:
            # agenda próxima tentativa para daqui 1 dia
            proxima = datetime.datetime.now() + datetime.timedelta(days=1)
            avancado["ultima_tentativa"] = proxima.isoformat()
            config["protecao_url_avancado"] = avancado
            helpers.salvar_config(config)
            await modal_inter.followup.send(
                f"{emoji.warn} Falha: {message}\n-# Próxima tentativa: <t:{int(proxima.timestamp())}:f>",
                ephemeral=True
            )

async def handle_toggle(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    is_enabled = config[helpers.CHAVE].get("ativado", False)
    if not is_enabled:
        av = config.get("protecao_url_avancado", {})
        if not av.get("url_nome"):
            await inter.response.send_message(f"{emoji.warn} Configure uma URL antes de ativar.", ephemeral=True)
            return
        if not av.get("token_user_id"):
            await inter.response.send_message(f"{emoji.warn} Configure uma conta antes de ativar.", ephemeral=True)
            return
    config[helpers.CHAVE]["ativado"] = not is_enabled
    helpers.salvar_config(config)
    await cog.display_panel(inter)

async def handle_set_url(cog, inter: disnake.MessageInteraction):
    await cog.display_url_panel(inter)

async def handle_set_token(cog, inter: disnake.MessageInteraction):
    await cog.display_token_panel(inter)

async def handle_set_log_channel(cog, inter: disnake.MessageInteraction):
    await cog.display_log_channel_panel(inter)

async def handle_token_select(cog, inter: disnake.MessageInteraction):
    if inter.values[0] == "__empty__":
        await inter.response.send_message("Nenhuma conta disponível. Adicione em Configurações > Tokens.", ephemeral=True)
        return
    config = helpers.carregar_config()
    config["protecao_url_avancado"]["token_user_id"] = inter.values[0]
    helpers.salvar_config(config)
    await cog.display_token_panel(inter)

async def handle_log_channel_select(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["protecao_url_avancado"]["canal_logs"] = int(inter.values[0])
    helpers.salvar_config(config)
    await cog.display_log_channel_panel(inter)

async def handle_log_channel_clear(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    config["protecao_url_avancado"]["canal_logs"] = None
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
            await inter.followup.send("Sem permissão para criar categoria.", ephemeral=True)
            return
    try:
        ch = await inter.guild.create_text_channel("logs-protecao-url", category=category,
                                                   overwrites={inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False)})
        config = helpers.carregar_config()
        config["protecao_url_avancado"]["canal_logs"] = ch.id
        helpers.salvar_config(config)
    except disnake.Forbidden:
        await inter.followup.send("Sem permissão para criar canal.", ephemeral=True)
        return
    await cog.display_log_channel_panel(inter)

async def handle_configure_url(cog, inter: disnake.MessageInteraction):
    modal = UrlConfigureModal(cog, inter)
    await inter.response.send_modal(modal)

async def handle_check_status(cog, inter: disnake.MessageInteraction):
    config = helpers.carregar_config()
    av = config.get("protecao_url_avancado", {})
    url_nome = av.get("url_nome")
    if not url_nome:
        await inter.response.send_message(f"{emoji.warn} Nenhuma URL configurada.", ephemeral=True)
        return
    token_user_id = av.get("token_user_id")
    if not token_user_id:
        await inter.response.send_message(f"{emoji.warn} Nenhuma conta configurada.", ephemeral=True)
        return
    tokens = db.get_document("tokens", {}).get("list", [])
    token_data = next((t for t in tokens if t["user_id"] == token_user_id), None)
    if not token_data:
        await inter.response.send_message(f"{emoji.warn} Conta não encontrada.", ephemeral=True)
        return
    await inter.response.defer()
    mgr = url_manager.URLManager(cog.bot)
    current = await mgr.get_current_vanity_code(inter.guild.id, token_data["token"])
    if current == url_nome:
        await inter.followup.send(f"{emoji.check} URL correta: discord.gg/{url_nome}")
    else:
        await inter.followup.send(
            f"{emoji.warn} URL alterada!\n**Atual:** {current or 'nenhuma'}\n**Configurada:** {url_nome}\n-# A proteção irá restaurar."
        )