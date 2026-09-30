import disnake
from disnake.ext import commands
import time
import asyncio
from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji
from functions.utils import utils

class Remove(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(
        name="remover", 
        description="Remover recursos", 
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(manage_roles=True)
    )
    async def remover(self, inter):
        pass

    @remover.sub_command_group(name="cargo", description="Gerenciar cargos (remover)")
    async def remover_cargo(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @remover_cargo.sub_command(name="user", description="Remover cargo de um membro do servidor")
    async def remover_cargo_user(self, inter: disnake.ApplicationCommandInteraction, cargo: disnake.Role, membro: disnake.Member):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message

        await msg_handler.wait(inter, send=True)
        try:
            await membro.remove_roles(cargo, reason=f"[Sync] Removido por {inter.user}")
            await msg_handler.success(inter, f"O cargo {cargo.mention} foi removido com sucesso de {membro.mention}!", send=False)
        except Exception:
            await msg_handler.error(inter, f"Não consegui remover {cargo.mention} de {membro.mention}. \n{emoji.warn} Verifique se meu cargo está acima de {cargo.mention}.", send=False)

    @remover_cargo.sub_command(name="all", description="Remover cargo de todos os membros do servidor")
    async def remover_cargo_all(self, inter: disnake.ApplicationCommandInteraction, cargo: disnake.Role):
        mode = db.get_document("custom_mode").get("mode")
        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")
        msg_handler = embed_message if mode == "embed" else message

        membros = [m for m in inter.guild.members if not m.bot and cargo in m.roles]
        total, sucesso, erro = len(membros), 0, 0
        
        # Rate limiting: Discord permite ~50 requests/segundo, mas vamos usar 15 para ser seguro
        # Processar em batches de 15 com delay de 1 segundo entre batches
        BATCH_SIZE = 15
        DELAY_BETWEEN_BATCHES = 1.0  # 1 segundo entre batches
        
        await msg_handler.wait(inter, send=True)
        start_time = time.time()

        async def atualizar_progresso():
            elapsed = time.time() - start_time
            avg_per_member = elapsed / max(sucesso + erro, 1)
            restantes = total - (sucesso + erro)
            eta_seconds = int(avg_per_member * restantes) if restantes > 0 else 0
            eta_unix = int(time.time() + eta_seconds)

            progress_text = (
                f"{emoji.loading} Progresso: `{sucesso}/{total}` membros tiveram {cargo.mention} removido\n"
                f"{emoji.wrong} Falha em `{erro}` membros.\n"
                f"{emoji.clock} Estimativa de término: <t:{eta_unix}:R>"
            )

            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    title=f"Removendo o cargo {cargo.name}",
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

        # Processar em batches com rate limiting
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = membros[batch_start:batch_end]
            
            # Processar batch atual
            for membro in batch:
                try:
                    await membro.remove_roles(cargo, reason=f"[Sync] Removido por {inter.user}")
                    sucesso += 1
                except Exception as e:
                    erro += 1
            
            # Atualizar progresso após cada batch
            await atualizar_progresso()
            
            # Rate limiting: aguardar antes do próximo batch (exceto no último)
            if batch_end < total:
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)

        final_text = (
            f"Cargo {cargo.mention} removido de `{sucesso}` membros.\n"
            f"{emoji.wrong} Falha em `{erro}` membros. (Total: `{total}`)\n"
            f"{emoji.clock} Finalizado <t:{int(time.time())}:R> - Iniciado <t:{int(start_time)}:R>"
        )
        await msg_handler.success(inter, final_text, send=False)

def setup(bot: commands.Bot):
    bot.add_cog(Remove(bot))
