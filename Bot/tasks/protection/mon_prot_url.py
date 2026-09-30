import asyncio
import datetime
import disnake
from disnake.ext import commands, tasks
from functions.emoji import emoji
from modules.protection.protecaogeral.url import helpers, url_manager
from ._common import enviar_log

class MonProtUrl(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._scan_task.start()

    def cog_unload(self):
        self._scan_task.cancel()

    @tasks.loop(minutes=5)
    async def _scan_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                await self._verificar_guild(guild)
            except Exception as e:
                print(f"[ProtecaoURL] Erro na guild {guild.id}: {e}")

    async def _verificar_guild(self, guild: disnake.Guild):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        if not dados.get("ativado"):
            return
        av = config.get("protecao_url_avancado", {})
        url_nome = av.get("url_nome")
        token_user_id = av.get("token_user_id")
        canal_logs_id = av.get("canal_logs")
        if not url_nome or not token_user_id:
            return

        # Cooldown de 1 dia
        ultima = av.get("ultima_tentativa")
        if ultima:
            try:
                if datetime.datetime.now() < datetime.datetime.fromisoformat(ultima):
                    return
            except:
                pass

        tokens = self.bot.cogs.get("TokensPanel")
        if not tokens:
            return
        from modules.settings.tokens.cog import TokensPanel
        token_list = TokensPanel._tokens_list()
        token_data = next((t for t in token_list if t["user_id"] == token_user_id), None)
        if not token_data:
            return

        mgr = url_manager.URLManager(self.bot)
        current = await mgr.get_current_vanity_code(guild.id, token_data["token"])
        if current != url_nome:
            success, msg = await mgr.set_vanity_url(
                guild.id, token_data["token"],
                token_data.get("password", ""), url_nome
            )
            if success:
                if canal_logs_id:
                    await enviar_log(guild, canal_logs_id, "Proteção URL - Restauração",
                                     [f"{emoji.reload} URL restaurada para discord.gg/{url_nome}",
                                      f"{emoji.members} Conta: {token_data['username']}"])
            else:
                proxima = datetime.datetime.now() + datetime.timedelta(days=1)
                av["ultima_tentativa"] = proxima.isoformat()
                config["protecao_url_avancado"] = av
                helpers.salvar_config(config)
                if canal_logs_id:
                    await enviar_log(guild, canal_logs_id, "Proteção URL - Falha",
                                     [f"{emoji.warn} Falha ao restaurar: {msg}",
                                      f"Próxima tentativa: <t:{int(proxima.timestamp())}:f>"])

    @commands.Cog.listener()
    async def on_guild_update(self, before: disnake.Guild, after: disnake.Guild):
        config = helpers.carregar_config()
        if not config.get(helpers.CHAVE, {}).get("ativado"):
            return
        av = config.get("protecao_url_avancado", {})
        if before.vanity_url_code == after.vanity_url_code:
            return
        # Detectada alteração
        await asyncio.sleep(1)
        executor = "Desconhecido"
        try:
            async for entry in after.audit_logs(action=disnake.AuditLogAction.guild_update, limit=5):
                if (disnake.utils.utcnow() - entry.created_at).total_seconds() <= 30:
                    u = entry.user
                    executor = f"{u.mention} ({u.id})" if u else "Desconhecido"
                    break
        except:
            pass
        canal_logs = av.get("canal_logs")
        if canal_logs:
            await enviar_log(after, canal_logs, "Proteção URL - Alteração Detectada",
                             [f"{emoji.warn} URL alterada por {executor}",
                              f"Antiga: {before.vanity_url_code or 'nenhuma'}",
                              f"Nova: {after.vanity_url_code or 'nenhuma'}",
                              "A proteção tentará restaurar em até 5 minutos."])

def setup(bot: commands.Bot):
    bot.add_cog(MonProtUrl(bot))