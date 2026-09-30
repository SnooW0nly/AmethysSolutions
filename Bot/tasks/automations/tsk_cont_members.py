import disnake
from disnake.ext import commands, tasks
from modules.automations.cont_members.helpers import load_config, formatar_nome_canal

class ContadorTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.contador_task.is_running():
            self.contador_task.start()

    def cog_unload(self):
        self.contador_task.cancel()

    @tasks.loop(minutes=10)
    async def contador_task(self):
        config = load_config()
        if not config.get("ativado", False):
            return

        estilo_global = int(config.get("estilo", 0))
        for contador in config.get("contadores", []):
            try:
                guild = self.bot.get_guild(contador["guild_id"])
                if not guild:
                    continue

                canal = guild.get_channel(contador["canal_id"])
                if not canal or not isinstance(canal, disnake.VoiceChannel):
                    continue

                cargo = guild.get_role(contador["cargo_id"])
                if not cargo:
                    continue

                membros_com_cargo = len([member for member in guild.members if cargo in member.roles])
                
                novo_nome = formatar_nome_canal(
                    contador.get('prefixo', 'Contador'),
                    membros_com_cargo,
                    estilo_global
                )
                if canal.name != novo_nome:
                    await canal.edit(name=novo_nome, reason="Atualização automática do contador de membros")
                    
            except Exception as e:
                print(f"Erro ao atualizar contador: {e}")

    @contador_task.before_loop
    async def before_contador_task(self):
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(ContadorTask(bot))
