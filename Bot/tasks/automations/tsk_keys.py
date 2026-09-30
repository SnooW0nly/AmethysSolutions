import disnake
from disnake.ext import commands, tasks
from datetime import datetime
import pytz

from modules.automations.keys import helpers

TIMEZONE = pytz.timezone("America/Sao_Paulo")


class KeysTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.limpar_expiradas.is_running():
            self.limpar_expiradas.start()
        if not self.alerta_estoque.is_running():
            self.alerta_estoque.start()

    def cog_unload(self):
        self.limpar_expiradas.cancel()
        self.alerta_estoque.cancel()

    # ── Limpa keys expiradas a cada hora ──

    @tasks.loop(hours=1)
    async def limpar_expiradas(self):
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return

        deletadas = helpers.deletar_keys_expiradas()
        if deletadas > 0:
            canal_logs_id = config.get("canal_logs")
            if canal_logs_id:
                canal = self.bot.get_channel(int(canal_logs_id))
                if canal:
                    embed = disnake.Embed(
                        title="♻️ Limpeza Automática de Keys",
                        description=f"**{deletadas}** key(s) expirada(s) foram removidas automaticamente.",
                        color=0xFEE75C,
                        timestamp=datetime.now(TIMEZONE),
                    )
                    embed.set_footer(text="Sistema de Keys • Limpeza Automática")
                    await canal.send(embed=embed)

    @limpar_expiradas.before_loop
    async def before_limpar(self):
        await self.bot.wait_until_ready()

    # ── Alerta de estoque baixo a cada 30min ──

    @tasks.loop(minutes=30)
    async def alerta_estoque(self):
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return

        limite = config.get("alerta_estoque_minimo", 0)
        if limite <= 0:
            return

        stats = helpers.estatisticas()
        disponiveis = stats["disponiveis"]

        if 0 < disponiveis <= limite:
            canal_logs_id = config.get("canal_logs")
            if canal_logs_id:
                canal = self.bot.get_channel(int(canal_logs_id))
                if canal:
                    embed = disnake.Embed(
                        title="⚠️ Estoque de Keys Baixo!",
                        description=(
                            f"Restam apenas **{disponiveis}** key(s) disponíveis!\n"
                            f"Acesse o painel de automações para criar mais."
                        ),
                        color=0xFF6B35,
                        timestamp=datetime.now(TIMEZONE),
                    )
                    embed.add_field(name="🔑 Total", value=str(stats["total"]), inline=True)
                    embed.add_field(name="✅ Ativas", value=str(stats["ativas"]), inline=True)
                    embed.add_field(name="📥 Usadas", value=str(stats["usadas"]), inline=True)
                    embed.set_footer(text="Sistema de Keys • Alerta de Estoque")
                    await canal.send(embed=embed)

    @alerta_estoque.before_loop
    async def before_alerta(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(KeysTask(bot))