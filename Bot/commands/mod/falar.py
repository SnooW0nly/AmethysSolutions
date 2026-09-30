import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils

class Falar(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="falar",
        description="Envia uma mensagem no canal atual.",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(manage_messages=True)
    )
    async def falar(
        self, 
        inter: disnake.CommandInteraction,
        mensagem: str = commands.Param(name="mensagem", description="Mensagem para enviar"),
        arquivo: disnake.Attachment = commands.Param(name="arquivo", description="Imagem, áudio, vídeo ou qualquer arquivo para anexar", default=None)
    ):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        try:
            content = mensagem
            files = []
            
            if arquivo:
                try:
                    file_obj = await arquivo.to_file()
                    files.append(file_obj)
                    
                    file_extension = arquivo.filename.split('.')[-1].lower() if '.' in arquivo.filename else ''
                    if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
                        content += f"\n\n{emoji.image} **Imagem:** {arquivo.filename}"
                    elif file_extension in ['mp3', 'wav', 'ogg', 'm4a', 'flac']:
                        content += f"\n\n{emoji.music} **Áudio:** {arquivo.filename}"
                    elif file_extension in ['mp4', 'avi', 'mov', 'wmv', 'webm']:
                        content += f"\n\n{emoji.play} **Vídeo:** {arquivo.filename}"
                    else:
                        content += f"\n\n{emoji.link} **Arquivo:** {arquivo.filename}"
                        
                except Exception as e:
                    content += f"\n\n{emoji.warn} **Erro ao processar arquivo:** {arquivo.filename}"

            await inter.channel.send(content=content, files=files, allowed_mentions=disnake.AllowedMentions.all())
            
            success_text = (
                f"{emoji.correct} Mensagem enviada com sucesso!"
            )
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=success_text,
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, allowed_mentions=disnake.AllowedMentions.none())
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(success_text),
                    **container_kwargs
                )
                await inter.edit_original_message(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True),
                    allowed_mentions=disnake.AllowedMentions.none(),
                )

        except Exception as e:
            await msg_handler.error(inter, f"Não foi possível enviar a mensagem.\n{emoji.warn} Verifique as permissões e tente novamente.", send=False)

def setup(bot: commands.Bot):
    bot.add_cog(Falar(bot))