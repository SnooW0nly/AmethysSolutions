import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils

class Lock(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="lock",
        description="Tranca o canal, impedindo que todos ou um cargo específico envie mensagens.",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(manage_channels=True)
    )
    async def lock(self, inter: disnake.CommandInteraction, cargo: disnake.Role = commands.Param(default=None, description="Cargo a ser trancado (opcional)")):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True, ephemeral=False)
        
        canal = inter.channel
        alvo = cargo if cargo else inter.guild.default_role
        try:
            # Obter as permissões atuais para preservar view_channel
            overwrite = canal.overwrites_for(alvo)
            # Apenas alterar permissões de envio, preservando view_channel
            overwrite.send_messages = False
            overwrite.send_messages_in_threads = False
            overwrite.create_public_threads = False
            overwrite.create_private_threads = False
            await canal.set_permissions(alvo, overwrite=overwrite)
            
            success_text = f"{emoji.correct} Canal trancado para {alvo.mention}! Eles não podem enviar mensagens ou criar tópicos."
            unlock_button = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Desbloquear",
                    emoji=emoji.unlock,
                    custom_id=f"unlock_{cargo.id if cargo else 'default'}"
                )
            )

            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=success_text,
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, components=[unlock_button])
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(success_text),
                    disnake.ui.Separator(),
                    unlock_button,
                    **container_kwargs
                )
                await inter.edit_original_message(components=[container])

        except Exception:
            await msg_handler.error(inter, f"Não foi possível trancar o canal para {alvo.mention}.\n{emoji.warn} Verifique permissões.", send=False)

    @commands.slash_command(
        name="lock_all",
        description="Tranca todos os canais de texto para todos ou para um cargo específico.",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(manage_channels=True)
    )
    async def lock_all(self, inter: disnake.CommandInteraction, cargo: disnake.Role = commands.Param(default=None, description="Cargo a ser trancado (opcional)")):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True, ephemeral=False)

        alvo = cargo if cargo else inter.guild.default_role
        success = 0
        failed = 0
        for ch in inter.guild.text_channels:
            try:
                # Obter as permissões atuais para preservar view_channel
                overwrite = ch.overwrites_for(alvo)
                # Apenas alterar permissões de envio, preservando view_channel
                overwrite.send_messages = False
                overwrite.send_messages_in_threads = False
                overwrite.create_public_threads = False
                overwrite.create_private_threads = False
                await ch.set_permissions(alvo, overwrite=overwrite)
                success += 1
            except Exception:
                failed += 1

        success_text = f"{emoji.correct} {success} canal(is) trancado(s) para {alvo.mention}."
        if failed:
            success_text += f"\n{emoji.warn} {failed} canal(is) não puderam ser trancados. Verifique permissões."

        if mode == "embed":
            embed_kwargs = {}
            if primary_color_hex:
                embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
            embed = disnake.Embed(
                description=success_text,
                **embed_kwargs
            )
            await inter.edit_original_message(embed=embed)
        else:
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(success_text),
                **container_kwargs
            )
            await inter.edit_original_message(components=[container])

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id.startswith("unlock_"):
            if not inter.user.guild_permissions.manage_channels:
                await inter.response.send_message("Você não tem permissão para usar este botão.", ephemeral=True)
                return

            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message

            cargo_id = inter.component.custom_id.split("_")[1]
            if cargo_id == "default":
                cargo = inter.guild.default_role
            else:
                cargo = inter.guild.get_role(int(cargo_id))
                if not cargo:
                    await inter.response.send_message("Cargo não encontrado.", ephemeral=True)
                    return
            
            await inter.response.defer()
            # Obter as permissões atuais para preservar view_channel
            overwrite = inter.channel.overwrites_for(cargo)
            # Apenas alterar permissões de envio, preservando view_channel
            overwrite.send_messages = True
            overwrite.send_messages_in_threads = True
            overwrite.create_public_threads = True
            overwrite.create_private_threads = True
            await inter.channel.set_permissions(cargo, overwrite=overwrite)
            
            await msg_handler.success(inter, f"Canal desbloqueado para {cargo.mention}!\n{emoji.member} Ação realizada por {inter.user.mention}", send=False)

def setup(bot: commands.Bot):
    bot.add_cog(Lock(bot))