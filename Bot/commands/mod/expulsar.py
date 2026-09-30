import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils


class Expulsar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="expulsar",
        description="Expulsa um membro do servidor.",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(kick_members=True)
    )
    async def expulsar(
        self, 
        inter: disnake.CommandInteraction,
        membro: disnake.Member = commands.Param(name="membro", description="Membro a ser expulso"),
        motivo: str = commands.Param(name="motivo", description="Motivo da expulsão", default="Não informado")
    ):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        if membro.id == inter.guild.owner_id:
            await msg_handler.error(inter, "Você não pode expulsar o dono do servidor!", send=False)
            return
        
        if inter.user.id != inter.guild.owner_id and inter.user.top_role <= membro.top_role:
            await msg_handler.error(inter, "Você só pode expulsar membros com cargo inferior ao seu!", send=False)
            return

        if inter.guild.me.top_role <= membro.top_role:
            await msg_handler.error(inter, "Não posso expulsar este membro pois meu cargo está abaixo do alvo!", send=False)
            return

        try:
            await membro.kick(reason=f"[Sync] {motivo} (Expulso por {inter.user.name})")
            await msg_handler.success(inter, f"O membro {membro.mention} foi expulso com sucesso!", send=False)
        except Exception:
            await msg_handler.error(inter, f"Não foi possível expulsar {membro.mention}.\n{emoji.warn} Verifique permissões e hierarquia.", send=False)


def setup(bot: commands.Bot):
    bot.add_cog(Expulsar(bot))