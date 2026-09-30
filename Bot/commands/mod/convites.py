import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils
from functions.perms import perms

class Convites(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="convites",
        guild_ids=[utils.obter_server_principal()]
    )
    async def convites(self, inter: disnake.CommandInteraction):
        pass

    @convites.sub_command(
        name="ver",
        description="Ver convites de um usuário."
    )
    async def ver_convites(
        self, 
        inter: disnake.CommandInteraction, 
        user: disnake.Member = commands.Param(name="user", description="Usuário para ver os convites", default=None)
    ):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        try:
            target_user = user or inter.user
            guild_id = str(inter.guild.id)
            
            convites_data = db.get_document("convites")
            if not convites_data or guild_id not in convites_data:
                await msg_handler.error(inter, f"Não há dados de convites para este servidor.", send=False)
                return

            guild_convites = convites_data[guild_id]
            user_id = str(target_user.id)
            
            # Verificar se o usuário tem dados de convites (como inviter)
            if user_id not in guild_convites.get("invites", {}):
                # Verificar se o usuário foi convidado por alguém (como member)
                if user_id in guild_convites.get("members", {}):
                    member_data = guild_convites["members"][user_id]
                    inviter_id = member_data.get("inviter") if isinstance(member_data, dict) else member_data
                    
                    if inviter_id == "Vanity Url":
                        inviter_text = "Vanity URL do servidor"
                    else:
                        try:
                            inviter = await self.bot.fetch_user(int(inviter_id))
                            inviter_text = f"{inviter.mention}"
                        except:
                            inviter_text = "Usuário Desconhecido"
                    
                    success_text = (
                        f"{emoji.member} **Dados de {target_user.mention}**\n\n"
                        f"{emoji.link} **Convidado por:** {inviter_text}\n"
                        f"{emoji.warn} **Este usuário ainda não convidou ninguém.**"
                    )
                else:
                    await msg_handler.error(inter, f"{target_user.mention} não possui dados de convites registrados.", send=False)
                    return
            else:
                user_invites = guild_convites["invites"][user_id]
                total = user_invites.get("total", 0)
                valid = user_invites.get("valid", 0)
                fake = user_invites.get("fake", 0)
                bonus = user_invites.get("bonus", 0)
                left = user_invites.get("left", 0)

                success_text = (
                    f"{emoji.member} **Convites de {target_user.mention}**\n\n"
                    f"{emoji.link} **Total:** `{total}`\n"
                    f"{emoji.correct} **Válidos:** `{valid}`\n"
                    f"{emoji.warn} **Fake:** `{fake}`\n"
                    f"{emoji.star} **Bônus:** `{bonus}`\n"
                    f"{emoji.minus} **Saídas:** `{left}`"
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
            import traceback
            print(f"Erro ao obter convites: {e}")
            traceback.print_exc()
            await msg_handler.error(inter, f"Não foi possível obter os convites.\n{emoji.warn} Verifique se o usuário possui convites registrados.", send=False)

    @convites.sub_command(
        name="resetar",
        description="Resetar convites de um usuário ou todos."
    )
    async def resetar_convites(
        self, 
        inter: disnake.CommandInteraction,
        user: disnake.Member = commands.Param(name="user", description="Usuário para resetar convites", default=None),
        all_users: bool = commands.Param(name="all", description="Resetar todos os convites do servidor", default=False)
    ):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        # Verificar permissão do bot
        if not await perms.check(inter.author.id):
            await msg_handler.error(inter, f"Você não tem permissão para usar este comando.", send=False)
            return

        try:
            guild_id = str(inter.guild.id)
            convites_data = db.get_document("convites")
            
            if not convites_data or guild_id not in convites_data:
                await msg_handler.error(inter, f"Não há dados de convites para este servidor.", send=False)
                return

            guild_convites = convites_data[guild_id]
            
            if all_users:
                # Resetar todos os convites
                guild_convites["invites"] = {}
                guild_convites["members"] = {}
                success_text = f"{emoji.correct} Todos os convites do servidor foram resetados!"
            else:
                if not user:
                    await msg_handler.error(inter, f"Você deve especificar um usuário ou usar `all=True` para resetar todos.", send=False)
                    return
                
                user_id = str(user.id)
                if user_id not in guild_convites.get("invites", {}):
                    await msg_handler.error(inter, f"{user.mention} não possui convites registrados.", send=False)
                    return

                # Remover convites do usuário específico
                del guild_convites["invites"][user_id]
                
                # Remover membros que foram convidados por este usuário
                members_to_remove = []
                for member_id, member_data in guild_convites.get("members", {}).items():
                    if member_data.get("inviter") == user_id:
                        members_to_remove.append(member_id)
                
                for member_id in members_to_remove:
                    del guild_convites["members"][member_id]
                
                success_text = f"{emoji.correct} Convites de {user.mention} foram resetados!"

            # Salvar no banco de dados
            db.update_document("convites", {"_id": convites_data["_id"]}, convites_data)
            
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
            import traceback
            print(f"Erro ao resetar convites: {e}")
            traceback.print_exc()
            await msg_handler.error(inter, f"Não foi possível resetar os convites.\n{emoji.warn} Erro: {str(e)}", send=False)

    @convites.sub_command(
        name="ranking",
        description="Ver ranking de convites do servidor."
    )
    async def ranking_convites(self, inter: disnake.CommandInteraction):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)

        try:
            guild_id = str(inter.guild.id)
            convites_data = db.get_document("convites")
            
            if not convites_data or guild_id not in convites_data:
                await msg_handler.error(inter, f"Não há dados de convites para este servidor.", send=False)
                return

            guild_convites = convites_data[guild_id]
            invites_data = guild_convites.get("invites", {})
            
            if not invites_data:
                await msg_handler.error(inter, f"Não há convites registrados neste servidor.", send=False)
                return

            # Criar ranking baseado em convites válidos
            ranking = []
            for user_id, user_invites in invites_data.items():
                try:
                    member = inter.guild.get_member(int(user_id))
                    if member:
                        valid_invites = user_invites.get("valid", 0)
                        ranking.append((member, valid_invites))
                except Exception as e:
                    continue

            # Ordenar por convites válidos (decrescente)
            ranking.sort(key=lambda x: x[1], reverse=True)
            
            if not ranking:
                await msg_handler.error(inter, f"Não há membros válidos no ranking.", send=False)
                return

            # Criar texto do ranking (top 10)
            ranking_text = f"{emoji.star} **Ranking de Convites**\n\n"
            for i, (member, valid_invites) in enumerate(ranking[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"`{i}.`"
                ranking_text += f"{medal} {member.mention} - `{valid_invites}` convites válidos\n"
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=ranking_text,
                    **embed_kwargs
                )
                await inter.edit_original_message(embed=embed, allowed_mentions=disnake.AllowedMentions.none())
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(ranking_text),
                    **container_kwargs
                )
                await inter.edit_original_message(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True),
                    allowed_mentions=disnake.AllowedMentions.none(),
                )

        except Exception:
            await msg_handler.error(inter, f"Não foi possível obter o ranking.\n{emoji.warn} Verifique se há dados de convites.", send=False)

def setup(bot: commands.Bot):
    bot.add_cog(Convites(bot)) 