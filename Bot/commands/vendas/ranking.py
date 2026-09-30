import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from modules.loja.cart.purchase_manager import PurchaseManager
from typing import List, Dict


class RankingCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.slash_command(
        name="ranking",
        description="Exibe o ranking de compradores da loja",
        guild_ids=[utils.obter_server_principal()]
    )
    async def ranking(
        self,
        inter: disnake.ApplicationCommandInteraction,
        tipo: str = commands.Param(
            default="valor",
            description="Tipo de ranking",
            choices=["valor", "quantidade"]
        )
    ):
        await inter.response.defer()
        
        # Obter todas as compras
        all_purchases = PurchaseManager.get_all_purchases()
        
        if not all_purchases:
            await inter.followup.send(
                f"{emoji.wrong} Ainda não há compras registradas!",
                ephemeral=True
            )
            return
        
        # Processar estatísticas por usuário
        user_stats = {}
        for purchase in all_purchases:
            user_id = purchase.get("user_id")
            if not user_id:
                continue
            
            if user_id not in user_stats:
                user_stats[user_id] = {
                    "total_spent": 0,
                    "total_items": 0,
                    "total_purchases": 0
                }
            
            user_stats[user_id]["total_spent"] += purchase.get("pricing", {}).get("final_price", 0)
            user_stats[user_id]["total_items"] += purchase.get("quantity", 0)
            user_stats[user_id]["total_purchases"] += 1
        
        # Ordenar baseado no tipo
        if tipo == "valor":
            sorted_users = sorted(
                user_stats.items(),
                key=lambda x: x[1]["total_spent"],
                reverse=True
            )[:10]  # Top 10
            title_emoji = emoji.dollar
            title_text = "Ranking por Valor Gasto"
            subtitle = "Top 10 clientes que mais gastaram"
        else:
            sorted_users = sorted(
                user_stats.items(),
                key=lambda x: x[1]["total_items"],
                reverse=True
            )[:10]  # Top 10
            title_emoji = emoji.cardbox
            title_text = "Ranking por Quantidade"
            subtitle = "Top 10 clientes que mais compraram itens"
        
        # Adicionar usuários ao ranking
        medals = ["🥇", "🥈", "🥉"]
        
        ranking_text = ""
        for i, (user_id, stats) in enumerate(sorted_users):
            position = i + 1
            medal = medals[i] if i < 3 else f"**{position}º**"
            
            try:
                user = await self.bot.fetch_user(int(user_id))
                user_name = user.name
            except:
                user_name = f"Usuário {user_id}"
            
            if tipo == "valor":
                value = f"R$ {stats['total_spent']:.2f}"
            else:
                value = f"{stats['total_items']} itens"
            
            ranking_text += f"{medal} {user_name}\n"
            ranking_text += f"└ {value} | {stats['total_purchases']} compras\n\n"
        
        # Adicionar posição do usuário atual se não estiver no top 10
        user_position = None
        user_position_text = ""
        for i, (user_id, _) in enumerate(sorted_users):
            if user_id == str(inter.author.id):
                user_position = i + 1
                break
        
        if user_position is None and str(inter.author.id) in user_stats:
            # Calcular posição real
            all_sorted = sorted(
                user_stats.items(),
                key=lambda x: x[1]["total_spent"] if tipo == "valor" else x[1]["total_items"],
                reverse=True
            )
            for i, (user_id, _) in enumerate(all_sorted):
                if user_id == str(inter.author.id):
                    user_position = i + 1
                    break
            
            if user_position and user_position > 10:
                user_data = user_stats[str(inter.author.id)]
                if tipo == "valor":
                    value = f"R$ {user_data['total_spent']:.2f}"
                else:
                    value = f"{user_data['total_items']} itens"
                
                user_position_text = f"{emoji.location} **Sua Posição:** {user_position}º lugar - {value}"
        
        # Adicionar estatísticas gerais
        total_revenue = sum(s["total_spent"] for s in user_stats.values())
        total_items = sum(s["total_items"] for s in user_stats.values())
        total_customers = len(user_stats)
        
        footer_text = f"Total: {total_customers} clientes | R$ {total_revenue:.2f} | {total_items} itens"
        
        # Verificar modo de exibição
        mode = db.get_document("custom_mode").get("mode", "components")
        
        if mode == "components":
            # Modo Components v2
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {title_emoji} {title_text}\n-# {subtitle}"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(ranking_text if ranking_text else "Nenhum dado disponível"),
                    **container_kwargs
                )
            ]
            
            # Adicionar posição do usuário se houver
            if user_position_text:
                components.append(
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(user_position_text),
                        **container_kwargs
                    )
                )
            
            # Adicionar footer
            components.append(
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"-# {footer_text}"),
                    **container_kwargs
                )
            )
            
            await inter.followup.send(components=components, ephemeral=True)
        else:
            # Modo Embed
            embed = disnake.Embed(
                title=f"{title_emoji} {title_text}",
                description=ranking_text if ranking_text else "Nenhum dado disponível",
                color=disnake.Color.gold()
            )
            
            if user_position_text:
                embed.add_field(
                    name=f"{emoji.location} Sua Posição",
                    value=user_position_text.replace(f"{emoji.location} **Sua Posição:** ", ""),
                    inline=False
                )
            
            embed.set_footer(text=footer_text)
            
            await inter.followup.send(embed=embed, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(RankingCommand(bot))