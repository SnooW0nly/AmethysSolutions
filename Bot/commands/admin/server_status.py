import disnake
from disnake.ext import commands
import json

from functions.message import message
from functions.perms import perms
from functions.server_check import exclude_from_check

class ServerStatusCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="server_status",
        description="Verifica o status de proteção do servidor.",
    )
    @exclude_from_check  # Este comando pode ser usado em qualquer servidor para verificação
    async def server_status(self, inter: disnake.ApplicationCommandInteraction):
        if not await perms.check_owner(inter.user.id):
            return await message.missing_perms(inter)
        
        # Lê o servidor principal do config
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
                main_server_id = config.get("bot", {}).get("server")
                
                if main_server_id:
                    main_server_id = int(main_server_id)
                    
                    # Verifica se o comando está sendo executado no servidor principal
                    is_main = inter.guild_id == main_server_id
                    
                    embed = disnake.Embed(
                        title="🔒 Status de Proteção do Servidor",
                        color=disnake.Color.green() if is_main else disnake.Color.orange()
                    )
                    
                    embed.add_field(
                        name="Servidor Principal",
                        value=f"ID: `{main_server_id}`",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="Servidor Atual",
                        value=f"ID: `{inter.guild_id}`\nNome: {inter.guild.name}",
                        inline=False
                    )
                    
                    embed.add_field(
                        name="Status",
                        value="✅ Este é o servidor principal!" if is_main else "⚠️ Este NÃO é o servidor principal!",
                        inline=False
                    )
                    
                    if not is_main:
                        embed.add_field(
                            name="Informação",
                            value="Os comandos (exceto /backup e /server_status) só funcionam no servidor principal.",
                            inline=False
                        )
                    
                    await inter.response.send_message(embed=embed, ephemeral=True)
                else:
                    embed = disnake.Embed(
                        title="❌ Erro",
                        description="Servidor principal não configurado no config.json",
                        color=disnake.Color.red()
                    )
                    await inter.response.send_message(embed=embed, ephemeral=True)
                    
        except Exception as e:
            embed = disnake.Embed(
                title="❌ Erro",
                description=f"Erro ao ler configuração: {str(e)}",
                color=disnake.Color.red()
            )
            await inter.response.send_message(embed=embed, ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(ServerStatusCommand(bot))
