import disnake
from disnake.ext import tasks, commands
import time

from functions.database import database as db
from functions.utils import utils


class CargoTemporarioTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.verificar_cargos_temporarios.start()

    def cog_unload(self):
        self.verificar_cargos_temporarios.cancel()

    @tasks.loop(minutes=1)
    async def verificar_cargos_temporarios(self):
        data = db.get_document("cargos_temporarios")
        if not data or "users" not in data:
            return

        agora = time.time()
        guild = self.bot.get_guild(utils.obter_server_principal())
        if not guild:
            return

        houve_alteracao = False
        users_para_deletar = []

        for user_id_str, roles in list(data["users"].items()):
            roles_mantidos = []

            for cargo_data in roles:
                if agora > cargo_data["expiration"]:
                    houve_alteracao = True
                    membro = guild.get_member(int(user_id_str))
                    if membro:
                        role = guild.get_role(cargo_data["role_id"])
                        if role:
                            try:
                                await membro.remove_roles(role)
                            except disnake.HTTPException:
                                pass
                else:
                    roles_mantidos.append(cargo_data)

            if roles_mantidos:
                data["users"][user_id_str] = roles_mantidos
            else:
                users_para_deletar.append(user_id_str)

        # Remove fora do loop para evitar mutação durante iteração
        for user_id_str in users_para_deletar:
            del data["users"][user_id_str]

        if houve_alteracao:
            db.save_document("cargos_temporarios", data)

    @verificar_cargos_temporarios.before_loop
    async def before_verificar(self):
        await self.bot.wait_until_ready()


def setup(bot: commands.Bot):
    bot.add_cog(CargoTemporarioTaskCog(bot))