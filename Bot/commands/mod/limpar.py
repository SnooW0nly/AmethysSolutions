import disnake
import time
import traceback
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils

class Limpar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="limpar",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(manage_messages=True)
    )
    async def limpar(self, inter: disnake.CommandInteraction):
        pass

    @limpar.sub_command(
        name="canal",
        description="Limpa mensagens de um canal.",
    )
    async def limpar_canal(
        self, 
        inter: disnake.CommandInteraction, 
        quantidade: int = commands.Param(name="quantidade", description="Quantidade de mensagens a limpar", min_value=1, max_value=1000)
    ):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)
        
        try:
            deleted_messages = await inter.channel.purge(limit=quantidade)
            total_deleted = len(deleted_messages)

            await inter.delete_original_message()

            success_text = (
                f"{emoji.correct} `{total_deleted}` mensagens foram apagadas com sucesso!\n"
                f"{emoji.member} Autor da ação: {inter.user.mention}"
            )
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=success_text,
                    **embed_kwargs
                )
                await inter.channel.send(embed=embed, allowed_mentions=disnake.AllowedMentions.none())
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(success_text),
                    **container_kwargs
                )
                await inter.channel.send(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True),
                    allowed_mentions=disnake.AllowedMentions.none(),
                )

        except Exception:
            await msg_handler.error(inter, f"Não foi possível apagar as mensagens.\n{emoji.warn} Verifique permissões.", send=False)

    @limpar.sub_command(
        name="dm",
        description="Limpa todas as mensagens do DM do usuário."
    )
    async def limpar_dm(
        self, 
        inter: disnake.CommandInteraction,
        user: disnake.Member = commands.Param(name="user", description="Usuário a ser limpo")
    ):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        try:
            dm_channel = await user.create_dm()
            msgs = await dm_channel.history(limit=None).flatten()
            
            bot_messages = [msg for msg in msgs if msg.author == inter.bot.user]
            
            for msg in bot_messages:
                await msg.delete()

            await msg_handler.success(inter, f"Todas as `{len(bot_messages)}` mensagens do bot no DM de {user.mention} foram apagadas!", send=False)
        except Exception:
            await msg_handler.error(inter, f"Não foi possível apagar as mensagens.\n{emoji.warn} Verifique permissões e se o usuário tem DMs abertos.", send=False)

def setup(bot: commands.Bot):
    bot.add_cog(Limpar(bot))
