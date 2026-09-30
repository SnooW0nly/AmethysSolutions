import disnake
from disnake.ext import commands
from datetime import timedelta
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils


class Castigar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        default_member_permissions=disnake.Permissions(moderate_members=True),
        guild_ids=[utils.obter_server_principal()]
    )
    async def castigo(self, inter: disnake.CommandInteraction):
        pass

    @castigo.sub_command(
        name="adicionar",
        description="Castiga (timeout) um membro por um tempo."
    )
    async def castigar(
        self, 
        inter: disnake.CommandInteraction,
        membro: disnake.Member = commands.Param(name="membro", description="Membro a ser castigado"),
        tempo: int = commands.Param(name="tempo", description="Tempo em minutos"),
        motivo: str = commands.Param(name="motivo", description="Motivo do castigo", default="Não informado")
    ):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        if membro.id == inter.guild.owner_id:
            await msg_handler.error(inter, "Você não pode castigar o dono do servidor!", send=False)
            return
        
        if inter.user.id != inter.guild.owner_id and inter.user.top_role <= membro.top_role:
            await msg_handler.error(inter, "Você só pode castigar membros com cargo inferior ao seu!", send=False)
            return
        
        if inter.guild.me.top_role <= membro.top_role:
            await msg_handler.error(inter, "Não posso castigar este membro pois meu cargo está abaixo do alvo!", send=False)
            return

        try:
            await membro.timeout(duration=timedelta(minutes=tempo), reason=f"[Sync] {motivo} (Castigado por {inter.user.name})")
            await msg_handler.success(inter, f"O membro {membro.mention} foi castigado por {tempo} minutos!", send=False)
        except Exception:
            await msg_handler.error(inter, f"Não foi possível castigar {membro.mention}.\n{emoji.warn} Verifique permissões e hierarquia.", send=False)

    @castigo.sub_command(
        name="remover",
        description="Remove o castigo (timeout) de um membro."
    )
    async def remover_castigo(
        self, 
        inter: disnake.CommandInteraction,
        membro: disnake.Member = commands.Param(name="membro", description="Membro para remover o castigo"),
        motivo: str = commands.Param(name="motivo", description="Motivo da remoção", default="Não informado")
    ):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        try:
            await membro.timeout(duration=None, reason=f"{motivo} (Castigo removido por {inter.user})")
            await msg_handler.success(inter, f"O castigo de {membro.mention} foi removido com sucesso!", send=False)
        except Exception as e:
            await msg_handler.error(inter, f"Não foi possível remover o castigo de {membro.mention}.\n{emoji.warn} Verifique permissões e hierarquia.", send=False)

def setup(bot: commands.Bot):
    bot.add_cog(Castigar(bot))