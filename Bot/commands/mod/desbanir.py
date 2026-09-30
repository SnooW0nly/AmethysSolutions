import disnake
import asyncio
import datetime
import time
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils


class Desbanir(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="desbanir",
        description="Desbane um usuário pelo ID.",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(ban_members=True)
    )
    async def desbanir(
        self, 
        inter: disnake.CommandInteraction,
        user_id: str = commands.Param(name="user_id", description="ID do usuário a ser desbanido")
    ):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        try:
            user = await inter.guild.fetch_ban(disnake.Object(id=int(user_id)))
            await inter.guild.unban(user.user)
            await msg_handler.success(inter, f"O usuário {user.user.mention} foi desbanido com sucesso!", send=False)
        except Exception:
            await msg_handler.error(inter, f"Não foi possível desbanir o usuário com ID {user_id}.\n{emoji.warn} Verifique se o ID está correto e se o usuário está banido.", send=False)


    @commands.slash_command(
        name="desbanirtodos",
        description="Desbane todos os usuários banidos do servidor.",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def desbanir_all(self, inter: disnake.CommandInteraction):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        try:
            bans = [entry async for entry in inter.guild.bans(limit=None)]
            total = len(bans)
            if total == 0:
                await msg_handler.success(inter, "Não há usuários banidos no servidor.", send=False)
                return

            sucesso = 0
            erro = 0
            start_time = time.time()

            async def atualizar_progresso():
                processados = sucesso + erro
                elapsed_seconds = max(time.time() - start_time, 0.001)
                avg_per = elapsed_seconds / max(processados, 1)
                restantes = total - processados
                eta_seconds = int(avg_per * restantes) if restantes > 0 else 0
                eta_unix = int(time.time() + eta_seconds)
                
                progress_text = (
                    f"{emoji.loading} Progresso: `{sucesso}/{total}` usuários desbanidos\n"
                    f"{emoji.wrong} Falha em `{erro}` usuários.\n"
                    f"{emoji.clock} Estimativa de término: <t:{eta_unix}:R>"
                )

                if mode == "embed":
                    embed_kwargs = {}
                    if primary_color_hex:
                        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                    embed = disnake.Embed(
                        title="Desbanindo todos os usuários",
                        description=progress_text,
                        **embed_kwargs
                    )
                    await inter.edit_original_message(embed=embed)
                else:
                    container_kwargs = {}
                    if primary_color_hex:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(progress_text),
                        **container_kwargs
                    )
                    await inter.edit_original_message(components=[container])

            for idx, ban_entry in enumerate(bans, 1):
                try:
                    await inter.guild.unban(ban_entry.user)
                    sucesso += 1
                except Exception:
                    erro += 1
                await asyncio.sleep(1)

                if idx % 5 == 0 or idx == total:
                    await atualizar_progresso()

            now_unix = int(time.time())
            texto = (
                f"`{sucesso}` usuários desbanidos com sucesso!\n"
                f"{emoji.wrong} `{erro}` usuários falharam. (Total: `{total}`)\n"
                f"{emoji.clock} Finalizado <t:{now_unix}:R> - Iniciado <t:{int(start_time)}:R>"
            )
            await msg_handler.success(inter, texto, send=False)

        except Exception:
            await msg_handler.error(inter, f"Não foi possível listar/desbanir os usuários.\n{emoji.warn} Verifique permissões.", send=False)


def setup(bot: commands.Bot):
    bot.add_cog(Desbanir(bot))