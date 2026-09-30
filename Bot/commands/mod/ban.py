import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils

class Banir(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="banir",
        description="Bane um membro do servidor.",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(ban_members=True)
    )
    async def banir(
        self, 
        inter: disnake.CommandInteraction, 
        membro: disnake.Member = commands.Param(name="membro", description="Membro a ser banido"),
        motivo: str = commands.Param(name="motivo", description="Motivo do banimento", default="Não informado")
    ):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        
        await msg_handler.wait(inter, send=True)

        if membro.id == inter.guild.owner_id:
            await msg_handler.error(inter, "Você não pode banir o dono do servidor!", send=False)
            return
        
        if inter.user.id != inter.guild.owner_id and inter.user.top_role <= membro.top_role:
            await msg_handler.error(inter, "Você só pode banir membros com cargo inferior ao seu!", send=False)
            return

        if inter.guild.me.top_role <= membro.top_role:
            await msg_handler.error(inter, "Não posso banir este membro pois meu cargo está abaixo do alvo!", send=False)
            return

        try:
            await membro.ban(reason=f"[Sync] {motivo} (Banido por {inter.user.name})")
            await msg_handler.success(inter, f"O membro {membro.mention} foi banido com sucesso!", send=False)
        except Exception:
            await msg_handler.error(inter, f"Não foi possível banir {membro.mention}.\n{emoji.warn} Verifique permissões e hierarquia.", send=False)


def setup(bot: commands.Bot):
    bot.add_cog(Banir(bot))