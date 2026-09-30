import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils


class Nuke(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="nuke",
        description="Limpa o canal atual recriando-o (todas as mensagens serão apagadas)",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(manage_channels=True)
    )
    async def nuke(self, inter: disnake.CommandInteraction):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        
        confirmation_text = "Você deseja nukar o canal atual?\n\n**Atenção**: Esta ação irá excluir e recriar completamente este canal.\nTodas as mensagens serão perdidas permanentemente."
        
        buttons = disnake.ui.ActionRow(
            disnake.ui.Button(label="Confirmar", emoji=emoji.correct, style=disnake.ButtonStyle.red, custom_id="Nuke_Confirm"),
            disnake.ui.Button(label="Cancelar", emoji=emoji.wrong, custom_id="Nuke_Cancel")
        )

        if mode == "embed":
            embed_kwargs = {}
            if primary_color_hex:
                embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
            embed = disnake.Embed(
                title="Confirmar Nuke",
                description=confirmation_text,
                **embed_kwargs
            )
            await inter.response.send_message(embed=embed, components=[buttons], ephemeral=True)
        else:
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(confirmation_text),
                disnake.ui.Separator(),
                buttons,
                **container_kwargs
            )
            await inter.response.send_message(components=[container], flags=disnake.MessageFlags(is_components_v2=True), ephemeral=True)

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id not in ["Nuke_Confirm", "Nuke_Cancel"]:
            return

        if custom_id == "Nuke_Cancel":
            if not inter.response.is_done():
                try:
                    await inter.response.defer_update()
                except Exception:
                    pass
            try:
                await inter.delete_original_message()
            except Exception:
                pass
            return
        
        if custom_id == "Nuke_Confirm":
            if not inter.response.is_done():
                try:
                    await inter.response.defer_update()
                except Exception:
                    pass
            try:
                await inter.delete_original_message()
            except Exception:
                pass

            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            msg_handler = embed_message if mode == "embed" else message
            
            canal_antigo = inter.channel
            try:
                novo_canal = await canal_antigo.clone(reason=f"Nuke solicitado por {inter.user}")
                await novo_canal.edit(position=canal_antigo.position, category=canal_antigo.category)
                await canal_antigo.delete(reason=f"Nuke solicitado por {inter.user}")
                
                success_text = f"{emoji.correct} Canal nukado com sucesso por {inter.user.mention}!"
                
                if mode == "embed":
                    embed_kwargs = {}
                    if primary_color_hex:
                        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                    embed = disnake.Embed(description=success_text, **embed_kwargs)
                    await novo_canal.send(embed=embed)
                else:
                    container_kwargs = {}
                    if primary_color_hex:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(success_text),
                        **container_kwargs
                    )
                    await novo_canal.send(components=[container], flags=disnake.MessageFlags(is_components_v2=True))
                    
            except Exception:
                # Se a clonagem falhar, o canal original ainda existe, então podemos enviar o erro lá.
                await msg_handler.error(inter, f"Não foi possível nukar o canal.\n{emoji.warn} Verifique permissões.", send=True, is_followup=True)


def setup(bot: commands.Cog):
    bot.add_cog(Nuke(bot))