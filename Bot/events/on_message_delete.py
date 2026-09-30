import disnake
import asyncio
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, buscar_executor_auditlog, verificar_guild
from functions.emoji import emoji


class OnMessageDelete(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message_delete")
    async def on_message_delete(self, message: disnake.Message):
        if message.guild is None or message.author.bot or not verificar_guild(message.guild.id):
            return

        canal_id = obter_canal_id("canal_de_logs_de_mensagens")
        if not canal_id:
            return
        conteudo = message.content[:1900] if message.content else "(sem conteúdo)"
        try:
            await asyncio.sleep(0.6)
        except Exception:
            pass

        def matcher(entry: disnake.AuditLogEntry) -> bool:
            try:
                if entry.action == disnake.AuditLogAction.message_delete:
                    target_id = getattr(getattr(entry, "target", None), "id", None)
                    if target_id != message.author.id:
                        return False
                    extra = getattr(entry, "extra", None)
                    extra_channel = getattr(extra, "channel", None)
                    extra_channel_id = getattr(extra_channel, "id", None) if extra_channel else getattr(extra, "channel_id", None)
                    return (extra_channel_id is None) or (extra_channel_id == message.channel.id)
                if entry.action == disnake.AuditLogAction.message_bulk_delete:
                    extra = getattr(entry, "extra", None)
                    extra_channel = getattr(extra, "channel", None)
                    extra_channel_id = getattr(extra_channel, "id", None) if extra_channel else getattr(extra, "channel_id", None)
                    return extra_channel_id == message.channel.id
            except Exception:
                return False
            return False

        executor = None
        for _ in range(3):
            executor = await buscar_executor_auditlog(
                message.guild,
                [disnake.AuditLogAction.message_delete, disnake.AuditLogAction.message_bulk_delete],
                matcher,
                max_age_seconds=120,
            )
            if executor:
                break
            try:
                await asyncio.sleep(0.8)
            except Exception:
                break

        if not executor:
            executor = message.author
            suffix = " (autoexcluiu)"
        else:
            suffix = ""
        executor_str = (
            (executor.mention if hasattr(executor, "mention") else str(executor))
            + (f" (`{executor.id}`)" if getattr(executor, "id", None) else "")
            + suffix
        ) if executor else "Não identificado"

        linhas = [
            f"{emoji.message} **Mensagem deletada em:** {message.channel.mention} (`{message.channel.id}`)",
            f"{emoji.member} **Executor:** {executor_str}",
            f"{emoji.member} **Autor:** {message.author.mention} (`{message.author.id}`)",
            f"{emoji.textc} **Conteúdo:**\n```\n{conteudo}\n```",
        ]
        await enviar_log(message.guild, canal_id, "Logs de Mensagens - Deletadas", linhas)


def setup(bot: commands.Bot):
    bot.add_cog(OnMessageDelete(bot))