import disnake
import asyncio
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
import pytz

from modules.automations.clean import helpers
from functions.database import database as db

class CleanTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.limpeza_task.is_running():
            self.limpeza_task.start()

    def cog_unload(self):
        self.limpeza_task.cancel()
    
    def restart_task(self):
        """Reinicia a task de limpeza."""
        self.limpeza_task.restart()

    @tasks.loop(minutes=1)
    async def limpeza_task(self):
        try:
            config = helpers.carregar_config()
            if not config.get("ativado", False):
                return

            canais = config.get("canais", {})
            if not canais:
                return
                
            agora = datetime.now(pytz.timezone('America/Sao_Paulo'))

            for canal_id, canal_config in canais.items():
                try:
                    await self._verificar_e_limpar_canal(canal_id, canal_config, agora)
                except Exception as e:
                    await helpers.enviar_log_erro(self.bot, f"Erro na limpeza automática do canal <#{canal_id}>: {str(e)}")
                    continue
        except Exception as e:
            await helpers.enviar_log_erro(self.bot, f"Erro na task de limpeza automática: {str(e)}")

    @limpeza_task.before_loop
    async def before_limpeza_task(self):
        await self.bot.wait_until_ready()

    async def _verificar_e_limpar_canal(self, canal_id: str, canal_config: dict, agora: datetime):
        try:
            canal = self.bot.get_channel(int(canal_id))
            if not isinstance(canal, disnake.TextChannel):
                return

            proxima_limpeza_str = canal_config.get("proxima_limpeza")
            if not proxima_limpeza_str:
                return

            proxima_limpeza_dt = datetime.fromisoformat(proxima_limpeza_str)

            if agora >= proxima_limpeza_dt:
                total_deleted = await self._executar_limpeza(canal)
                
                config = helpers.carregar_config()
                if canal_id in config["canais"]:
                    intervalo_minutos = config["canais"][canal_id].get("intervalo_minutos", 1440)
                    nova_proxima_limpeza = agora + timedelta(minutes=intervalo_minutos)
                    config["canais"][canal_id]["proxima_limpeza"] = nova_proxima_limpeza.isoformat()
                    helpers.salvar_config(config)
                    
                    await helpers.enviar_log_sucesso(self.bot, canal, total_deleted, intervalo_minutos, nova_proxima_limpeza)

        except Exception as e:
            await helpers.enviar_log_erro(self.bot, f"Erro ao verificar canal <#{canal_id}>: {str(e)}")

    async def _executar_limpeza(self, canal: disnake.TextChannel) -> int:
        try:
            total_deleted = 0
            
            async for message in canal.history(limit=None):
                if not message.pinned:
                    try:
                        await message.delete()
                        total_deleted += 1
                        await asyncio.sleep(0.1)
                    except disnake.HTTPException:
                        continue
            
            from functions.emoji import emoji
            
            mode = db.get_document("custom_mode").get("mode")
            description = f"{emoji.correct} `{total_deleted}` mensagens foram apagadas automaticamente!\n{emoji.clock} Limpeza automática programada"

            if mode == "embed":
                primary_color_hex = db.get_document("custom_colors").get("primary", "#5865F2")
                embed = disnake.Embed(
                    title="Limpeza Automática",
                    description=description,
                    color=disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                )
                system_message = await canal.send(
                    embed=embed, 
                    components=[disnake.ui.ActionRow(disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, custom_id="Limpeza_SystemBadge", disabled=True))]
                )
            else:
                system_message = await canal.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(description)
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, custom_id="Limpeza_SystemBadge", disabled=True)
                        )
                    ]
                )
            
            return total_deleted

        except Exception as e:
            await helpers.enviar_log_erro(self.bot, f"Erro ao executar limpeza do canal #{canal.name}: {str(e)}")
            return 0

def setup(bot: commands.Bot):
    bot.add_cog(CleanTaskCog(bot))
