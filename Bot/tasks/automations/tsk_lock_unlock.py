import disnake
from disnake.ext import commands, tasks
from datetime import datetime, timedelta
import pytz

from modules.automations.lock_unlock import helpers
from functions.emoji import emoji
from functions.database import database as db

class LockUnlockTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.lockunlock_task.is_running():
            self.lockunlock_task.start()

    def cog_unload(self):
        self.lockunlock_task.cancel()
    
    @tasks.loop(minutes=1)
    async def lockunlock_task(self):
        try:
            config = helpers.carregar_config()
            if not config.get("ativado", False):
                return

            canais = config.get("canais", {})
            if not canais:
                return

            agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
            hora_atual = agora.time()

            for canal_id, canal_config in canais.items():
                try:
                    canal = self.bot.get_channel(int(canal_id))
                    if not canal or not isinstance(canal, disnake.TextChannel):
                        continue

                    horario_lock_str = canal_config.get("horario_lock")
                    horario_unlock_str = canal_config.get("horario_unlock")

                    if not horario_lock_str or not horario_unlock_str:
                        continue
                    
                    lock_time = datetime.strptime(horario_lock_str, "%H:%M").time()
                    unlock_time = datetime.strptime(horario_unlock_str, "%H:%M").time()
                    
                    deve_estar_bloqueado = False
                    if lock_time < unlock_time:  # Lock durante o dia
                        if lock_time <= hora_atual < unlock_time:
                            deve_estar_bloqueado = True
                    else:  # Lock durante a noite (atravessa a meia-noite)
                        if hora_atual >= lock_time or hora_atual < unlock_time:
                            deve_estar_bloqueado = True
                    
                    overwrite = canal.overwrites_for(canal.guild.default_role)
                    esta_bloqueado = overwrite.send_messages is False
                    
                    ultimo_estado = canal_config.get("ultimo_estado")
                    novo_estado = "lock" if deve_estar_bloqueado else "unlock"

                    if novo_estado != ultimo_estado:
                        await self._aplicar_lockunlock(canal, novo_estado)
                        config = helpers.carregar_config()
                        config["canais"][canal_id]["ultimo_estado"] = novo_estado
                        helpers.salvar_config(config)

                        horario_agendado = horario_lock_str if novo_estado == 'lock' else horario_unlock_str
                        
                        proxima_execucao_dt = agora.replace(hour=int(horario_agendado[:2]), minute=int(horario_agendado[3:]), second=0, microsecond=0)
                        if agora > proxima_execucao_dt:
                            proxima_execucao_dt += timedelta(days=1)
                            
                        await self._enviar_log_sucesso(canal, novo_estado, horario_agendado, proxima_execucao_dt)

                except Exception as e:
                    await self._enviar_log_erro(f"Erro no lock/unlock automático do canal <#{canal_id}>: {str(e)}")
                    continue
        except Exception as e:
            await self._enviar_log_erro(f"Erro na task de lock/unlock automática: {str(e)}")

    async def _aplicar_lockunlock(self, canal: disnake.TextChannel, modo: str):
        try:
            overwrite = canal.overwrites_for(canal.guild.default_role)
            overwrite.send_messages = False if modo == "lock" else True
            await canal.set_permissions(canal.guild.default_role, overwrite=overwrite, reason="Lock/Unlock automático")
            
            mode = db.get_document("custom_mode").get("mode")
            description = f"{emoji.lock if modo == 'lock' else emoji.unlock} Canal {'bloqueado' if modo == 'lock' else 'desbloqueado'} automaticamente!\n{emoji.clock} Lock/Unlock automático programado"
            
            if mode == "embed":
                primary_color_hex = db.get_document("custom_colors").get("primary", "#5865F2")
                embed = disnake.Embed(
                    description=description,
                    color=disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                )
                await canal.send(
                    embed=embed,
                    components=[disnake.ui.ActionRow(disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, custom_id="LockUnlock_SystemBadge", disabled=True))]
                )
            else:
                await canal.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(description)
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, custom_id="LockUnlock_SystemBadge", disabled=True)
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
        except Exception as e:
            await self._enviar_log_erro(f"Erro ao aplicar lock/unlock no canal #{canal.name}: {str(e)}")

    async def _enviar_log_sucesso(self, canal: disnake.TextChannel, modo: str, horario: str, proxima_execucao: datetime):
        try:
            config = helpers.carregar_config()
            if not config.get("logs_ativados", True):
                return
            
            canal_logs = await helpers.obter_canal_logs(self.bot)
            if not canal_logs:
                return

            mode = db.get_document("custom_mode").get("mode")
            description = (
                f"**Canal:** {canal.mention}\n"
                f"**Ação:** `{modo}`\n"
                f"**Horário configurado:** `{horario}`\n"
                f"**Próxima execução:** <t:{int(proxima_execucao.timestamp())}:f> (<t:{int(proxima_execucao.timestamp())}:R>)"
            )

            if mode == "embed":
                primary_color_hex = db.get_document("custom_colors").get("primary", "#5865F2")
                embed = disnake.Embed(
                    title=f"Lock/Unlock Automático de Canais",
                    description=description,
                    color=disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                )
                await canal_logs.send(
                    embed=embed,
                    components=[disnake.ui.ActionRow(disnake.ui.Button(label="Desativar Logs", style=disnake.ButtonStyle.red, custom_id="LockUnlock_DesativarLogsViaLog"))]
                )
            else:
                await canal_logs.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Lock/Unlock Automático de Canais"),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay(description),
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Desativar Logs", style=disnake.ButtonStyle.red, custom_id="LockUnlock_DesativarLogsViaLog")
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
        except Exception:
            pass

    async def _enviar_log_erro(self, mensagem: str):
        try:
            config = helpers.carregar_config()
            if not config.get("logs_ativados", True):
                return
            
            canal_logs = await helpers.obter_canal_logs(self.bot)
            if not canal_logs:
                return
            
            mode = db.get_document("custom_mode").get("mode")

            if mode == "embed":
                danger_color_hex = db.get_document("custom_colors").get("danger", "#dc3545")
                embed = disnake.Embed(
                    title=f"{emoji.wrong} Erro no Lock/Unlock Automático",
                    description=mensagem,
                    color=disnake.Colour(int(danger_color_hex.replace("#", ""), 16))
                )
                await canal_logs.send(
                    embed=embed,
                    components=[disnake.ui.ActionRow(disnake.ui.Button(label="Desativar Logs", style=disnake.ButtonStyle.red, custom_id="LockUnlock_DesativarLogsViaLog"))]
                )
            else:
                await canal_logs.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.wrong} Erro no Lock/Unlock Automático\n\n{mensagem}"),
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Desativar Logs", style=disnake.ButtonStyle.red, custom_id="LockUnlock_DesativarLogsViaLog")
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
        except Exception:
            pass

    @tasks.loop(minutes=1)
    async def before_lockunlock_task(self):
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(LockUnlockTask(bot))
