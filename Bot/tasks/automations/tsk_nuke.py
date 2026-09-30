import disnake
import asyncio
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
import pytz

from modules.automations.nuke import helpers
from functions.database import database as db

class NukeTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.nuke_task.is_running():
            self.nuke_task.start()

    def cog_unload(self):
        self.nuke_task.cancel()
    
    def restart_task(self):
        """Reinicia a task de nuke."""
        self.nuke_task.restart()

    @tasks.loop(minutes=1)
    async def nuke_task(self):
        try:
            config = helpers.carregar_config()
            if not config.get("ativado", False):
                return

            canais = config.get("canais", {})
            if not canais:
                return
                
            agora = datetime.now(pytz.timezone('America/Sao_Paulo'))

            for canal_id, canal_config in list(canais.items()):
                try:
                    await self._verificar_e_nukar_canal(canal_id, canal_config, agora)
                except Exception as e:
                    await helpers.enviar_log_erro(self.bot, f"Erro no nuke automático do canal <#{canal_id}>: {str(e)}")
                    continue
        except Exception as e:
            await helpers.enviar_log_erro(self.bot, f"Erro na task de nuke automático: {str(e)}")

    @nuke_task.before_loop
    async def before_nuke_task(self):
        await self.bot.wait_until_ready()

    async def _verificar_e_nukar_canal(self, canal_id: str, canal_config: dict, agora: datetime):
        try:
            proxima_nuke_str = canal_config.get("proxima_nuke")
            if not proxima_nuke_str:
                return

            proxima_nuke_dt = datetime.fromisoformat(proxima_nuke_str)

            if agora >= proxima_nuke_dt:
                canal = self.bot.get_channel(int(canal_id))
                if not isinstance(canal, disnake.TextChannel):
                    return

                novo_canal = await self._executar_nuke(canal)
                
                config = helpers.carregar_config()
                if canal_id in config["canais"]:
                    intervalo_minutos = config["canais"][canal_id].get("intervalo_minutos", 1440)
                    nova_proxima_nuke = agora + timedelta(minutes=intervalo_minutos)
                    
                    # Remove a configuração antiga e adiciona a nova com o ID do novo canal
                    config_canal_antigo = config["canais"].pop(canal_id)
                    config_canal_antigo["proxima_nuke"] = nova_proxima_nuke.isoformat()
                    config["canais"][str(novo_canal.id)] = config_canal_antigo
                    
                    helpers.salvar_config(config)
                    
                    await helpers.enviar_log_sucesso(self.bot, canal, novo_canal, intervalo_minutos, nova_proxima_nuke)

        except Exception as e:
            await helpers.enviar_log_erro(self.bot, f"Erro ao verificar canal <#{canal_id}>: {str(e)}")

    async def _executar_nuke(self, canal: disnake.TextChannel) -> disnake.TextChannel:
        try:
            posicao = canal.position
            novo_canal = await canal.clone(reason="Nuke automático")
            await novo_canal.edit(position=posicao, reason="Ajustando posição após nuke")
            await canal.delete(reason="Nuke automático")
            
            from functions.emoji import emoji
            mode = db.get_document("custom_mode").get("mode")
            description = f"{emoji.correct} Este canal foi recriado (nukado) com sucesso!\n{emoji.clock} Nuke automático programado"

            if mode == "embed":
                primary_color_hex = db.get_document("custom_colors").get("primary", "#5865F2")
                embed = disnake.Embed(
                    description=description,
                    color=disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                )
                await novo_canal.send(
                    embed=embed,
                    components=[disnake.ui.ActionRow(disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, custom_id="Nuke_SystemBadge", disabled=True))]
                )
            else:
                await novo_canal.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(description)
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, custom_id="Nuke_SystemBadge", disabled=True)
                        )
                    ]
                )
            
            return novo_canal

        except Exception as e:
            await helpers.enviar_log_erro(self.bot, f"Erro ao executar nuke do canal #{canal.name}: {str(e)}")
            raise

def setup(bot: commands.Bot):
    bot.add_cog(NukeTaskCog(bot))
