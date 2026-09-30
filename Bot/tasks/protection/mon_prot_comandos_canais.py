import asyncio
import time
from typing import Optional

import disnake
from disnake.ext import commands, tasks

from functions.emoji import emoji
from ._common import enviar_log
from modules.protection.protecaogeral.comandoscanais import helpers


class MonProtComandosCanais(commands.Cog):
    """
    Varre todos os canais do servidor a cada 1 minuto e garante que a permissão
    'use_application_commands' (Usar Comandos de Aplicativos Externos) esteja
    NEGADA para @everyone e para todos os cargos não imunes em cada canal.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._scan_task.start()

    def cog_unload(self):
        self._scan_task.cancel()

    @tasks.loop(minutes=1)
    async def _scan_task(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                await self._varrer_guild(guild)
            except Exception as e:
                print(f"[ComandosCanais] Erro ao varrer guild {guild.id}: {e}")

    async def _varrer_guild(self, guild: disnake.Guild):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get("comandos_canais_avancado", {})

        if not dados.get("ativado", False):
            return

        cargos_imunes_ids: set[int] = set(avancado.get("cargos_imunes", []))
        canal_logs_id: Optional[int] = avancado.get("canal_logs")

        alteracoes: list[str] = []

        # Canais de texto, voz, fórum, stage e anúncios
        canais = [
            c for c in guild.channels
            if isinstance(c, (
                disnake.TextChannel,
                disnake.VoiceChannel,
                disnake.StageChannel,
                disnake.ForumChannel,
                disnake.NewsChannel,
            ))
        ]

        for canal in canais:
            try:
                await self._corrigir_canal(canal, guild, cargos_imunes_ids, alteracoes)
            except disnake.Forbidden:
                pass
            except Exception as e:
                print(f"[ComandosCanais] Erro no canal {canal.id}: {e}")
            # Pequeno sleep para não estrangular a API
            await asyncio.sleep(0.1)

        if alteracoes and canal_logs_id:
            linhas = [
                f"{emoji.shield} **Varredura automática** — comandos externos bloqueados",
                f"{emoji.calendar} **Servidor:** {guild.name} ({guild.id})",
                "",
                *alteracoes[:20],  # Limitar para evitar mensagens gigantes
            ]
            if len(alteracoes) > 20:
                linhas.append(f"-# ... e mais {len(alteracoes) - 20} correção(ões) não exibidas.")
            await enviar_log(guild, canal_logs_id, "Proibir Comandos Externos - Varredura", linhas)

    async def _corrigir_canal(
        self,
        canal: disnake.abc.GuildChannel,
        guild: disnake.Guild,
        cargos_imunes_ids: set[int],
        alteracoes: list[str],
    ):
        """
        Para o canal dado, garante que use_application_commands = False
        para @everyone e para todos os cargos não imunes que estejam nos overwrites.
        """
        mudancas_feitas = False

        # Copiar overwrites atuais para modificar
        overwrites = dict(canal.overwrites)

        # --- @everyone ---
        ow_everyone = overwrites.get(guild.default_role, disnake.PermissionOverwrite())
        if ow_everyone.use_application_commands is not False:
            ow_everyone.use_application_commands = False
            overwrites[guild.default_role] = ow_everyone
            mudancas_feitas = True

        # --- Cada cargo nos overwrites ---
        for target, ow in list(overwrites.items()):
            if not isinstance(target, disnake.Role):
                continue
            if target.id == guild.default_role.id:
                continue  # já tratado acima
            if target.id in cargos_imunes_ids:
                continue

            if ow.use_application_commands is not False:
                ow.use_application_commands = False
                overwrites[target] = ow
                mudancas_feitas = True

        # --- Cargos do servidor que ainda não têm overwrite no canal ---
        for role in guild.roles:
            if role.id == guild.default_role.id:
                continue
            if role.id in cargos_imunes_ids:
                continue
            if role in overwrites:
                continue  # já foi tratado acima
            # Só criar overwrite se o cargo tiver a permissão positiva
            # (evita criar overwrites desnecessários para cargos sem permissão)
            if role.permissions.use_application_commands:
                ow_role = disnake.PermissionOverwrite(use_application_commands=False)
                overwrites[role] = ow_role
                mudancas_feitas = True

        if mudancas_feitas:
            try:
                await canal.edit(
                    overwrites=overwrites,
                    reason="Proteção: bloqueio automático de comandos externos"
                )
                alteracoes.append(
                    f"{emoji.textc} **Canal corrigido:** <#{canal.id}> (`{canal.name}`)"
                )
            except disnake.Forbidden:
                alteracoes.append(
                    f"{emoji.wrong} **Sem permissão:** <#{canal.id}> (`{canal.name}`)"
                )
            except Exception as e:
                alteracoes.append(
                    f"{emoji.wrong} **Erro em** `{canal.name}`: {str(e)[:60]}"
                )

    # Listener: corrigir imediatamente quando uma permissão é alterada em um canal
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: disnake.abc.GuildChannel, after: disnake.abc.GuildChannel):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        if not dados.get("ativado", False):
            return

        guild = after.guild
        avancado = config.get("comandos_canais_avancado", {})
        cargos_imunes_ids: set[int] = set(avancado.get("cargos_imunes", []))
        canal_logs_id: Optional[int] = avancado.get("canal_logs")

        # Verificar se alguém habilitou use_application_commands em algum overwrite
        precisa_corrigir = False
        for target, ow in after.overwrites.items():
            if isinstance(target, disnake.Role):
                if target.id in cargos_imunes_ids:
                    continue
            if ow.use_application_commands is True:
                precisa_corrigir = True
                break

        if not precisa_corrigir:
            return

        # Pequeno delay para o audit log ser registrado
        await asyncio.sleep(1.0)

        alteracoes: list[str] = []
        await self._corrigir_canal(after, guild, cargos_imunes_ids, alteracoes)

        # Tentar identificar executor via audit log
        executor_str = "Desconhecido"
        try:
            agora = disnake.utils.utcnow()
            async for entry in guild.audit_logs(action=disnake.AuditLogAction.channel_update, limit=5):
                if getattr(entry, "target", None) and entry.target.id == after.id:
                    if (agora - entry.created_at).total_seconds() <= 30:
                        u = entry.user
                        executor_str = f"{u.mention} ({u.id})" if u else "Desconhecido"
                        break
        except Exception:
            pass

        if alteracoes and canal_logs_id:
            linhas = [
                f"{emoji.warn} **Permissão de comandos externos foi liberada manualmente e revertida**",
                f"{emoji.member} **Executor:** {executor_str}",
                f"{emoji.textc} **Canal:** <#{after.id}> (`{after.name}`)",
            ]
            await enviar_log(guild, canal_logs_id, "Proibir Comandos Externos - Reversão", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(MonProtComandosCanais(bot))