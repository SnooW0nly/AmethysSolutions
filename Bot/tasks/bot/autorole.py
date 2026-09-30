import disnake
from disnake.ext import commands
from functions.database import database

class AutoRoleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: disnake.Member):
        if member.bot:
            return

        cargos_data = database.get_document("cargos")
        
        if not cargos_data:
            print("Documento 'cargos' não encontrado no banco de dados.")
            return

        role_id = cargos_data.get("cargo_auto_role")

        if role_id:
            guild = member.guild
            role = guild.get_role(int(role_id))

            if role:
                try:
                    await member.add_roles(role)
                except disnake.Forbidden:
                    print(f"Não foi possível adicionar o cargo {role.name} para {member.display_name} por falta de permissões.")
                except disnake.HTTPException as e:
                    print(f"Ocorreu um erro ao tentar adicionar o cargo: {e}")
            else:
                print(f"O cargo com ID {role_id} não foi encontrado no servidor.")

def setup(bot: commands.Bot):
    bot.add_cog(AutoRoleCog(bot))
