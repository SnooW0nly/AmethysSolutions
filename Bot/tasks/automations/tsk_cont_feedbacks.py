import asyncio

import disnake
from disnake.ext import commands, tasks

from functions.database import database as db
from modules.automations.cont_feedbacks import helpers


class ContFeedbacksTask(commands.Cog):
    """
    Responsável por monitorar o canal de feedbacks e manter os contadores
    (canais/categorias) atualizados automaticamente.

    Separado do cog principal de UI para isolar a lógica de background.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cached_count: int = 0
        self._update_lock = asyncio.Lock()

    # ──────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.contador_feedbacks_task.is_running():
            self.contador_feedbacks_task.start()

    def cog_unload(self):
        self.contador_feedbacks_task.cancel()

    # ──────────────────────────────────────────────────────────────
    # Task periódica (a cada 10 minutos)
    # ──────────────────────────────────────────────────────────────

    @tasks.loop(minutes=10)
    async def contador_feedbacks_task(self):
        config = helpers.carregar_config()
        if not config.get("ativado", False) or not config.get("contadores"):
            return

        async with self._update_lock:
            count = await helpers.contar_mensagens_feedback(self.bot)
            self._cached_count = count
            await self._aplicar_contadores(config, count)

    @contador_feedbacks_task.before_loop
    async def before_task(self):
        await self.bot.wait_until_ready()

    # ──────────────────────────────────────────────────────────────
    # Lógica de aplicação dos contadores
    # ──────────────────────────────────────────────────────────────

    async def _aplicar_contadores(self, config: dict, count: int):
        """Aplica a contagem a todos os canais/categorias configurados."""
        estilo = config.get("estilo", 0)
        for contador in config.get("contadores", []):
            try:
                guild = self.bot.get_guild(contador["guild_id"])
                if not guild:
                    continue
                target = guild.get_channel(contador["target_id"])
                if not target:
                    continue
                if not isinstance(target, (disnake.VoiceChannel, disnake.TextChannel, disnake.CategoryChannel)):
                    continue
                novo_nome = helpers.formatar_nome_contador(contador.get("prefixo", "Feedbacks"), count, estilo)
                if target.name != novo_nome:
                    await target.edit(name=novo_nome, reason="Atualização automática do contador de feedbacks")
            except disnake.HTTPException:
                continue
            except Exception as e:
                print(f"[ContFeedbacks] Erro ao atualizar contador: {e}")

    async def atualizar_agora(self, guild: disnake.Guild):
        """Força atualização imediata dos contadores para um servidor."""
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return
        async with self._update_lock:
            count = await helpers.contar_mensagens_feedback(self.bot)
            self._cached_count = count
            await self._aplicar_contadores(config, count)

    # ──────────────────────────────────────────────────────────────
    # Listeners: on_message / on_message_delete (atualização em tempo real)
    # ──────────────────────────────────────────────────────────────

    async def _checar_e_atualizar(self, channel_id: int, guild: disnake.Guild):
        """Verifica se o canal é o de feedbacks e dispara atualização se necessário."""
        canais_config = db.get_document("canais") or {}
        canal_feedback_id = canais_config.get("canal_de_feedback")
        if not canal_feedback_id or channel_id != int(canal_feedback_id):
            return
        config = helpers.carregar_config()
        if not config.get("ativado", False) or not config.get("contadores"):
            return
        asyncio.create_task(self.atualizar_agora(guild))

    @commands.Cog.listener("on_message")
    async def on_feedback_novo(self, msg: disnake.Message):
        if msg.author.bot or not msg.guild:
            return
        await self._checar_e_atualizar(msg.channel.id, msg.guild)

    @commands.Cog.listener("on_message_delete")
    async def on_feedback_deletado(self, msg: disnake.Message):
        if not msg.guild:
            return
        await self._checar_e_atualizar(msg.channel.id, msg.guild)

    @commands.Cog.listener("on_bulk_message_delete")
    async def on_feedback_bulk_delete(self, messages: list[disnake.Message]):
        if not messages or not messages[0].guild:
            return
        await self._checar_e_atualizar(messages[0].channel.id, messages[0].guild)


def setup(bot: commands.Bot):
    bot.add_cog(ContFeedbacksTask(bot))