import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from modules.loja.cart.purchase_manager import PurchaseManager
from datetime import datetime
from typing import Optional
from modules.loja.saldo.balance_manager import BalanceManager


class PerfilCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.slash_command(
        name="perfil",
        description="Exibe o perfil de compras de um membro",
        guild_ids=[utils.obter_server_principal()]
    )
    async def perfil(
        self,
        inter: disnake.ApplicationCommandInteraction,
        membro: Optional[disnake.Member] = commands.Param(
            default=None,
            description="Membro para ver o perfil (deixe vazio para ver o seu)"
        )
    ):
        await inter.response.defer()
        
        # Se não especificar membro, usar o autor
        target = membro or inter.author
        
        # Obter estatísticas do usuário
        user_stats = PurchaseManager.get_user_statistics(target.id)
        
        if not user_stats.get("total_purchases"):
            if target.id == inter.author.id:
                msg = f"{emoji.wrong} Você ainda não fez nenhuma compra!"
            else:
                msg = f"{emoji.wrong} {target.mention} ainda não fez nenhuma compra!"
            
            await inter.followup.send(msg, ephemeral=True)
            return
        
        # Obter histórico de compras
        purchases = PurchaseManager.get_user_purchases(target.id, limit=5)
        
        # Verificar modo de exibição
        mode = db.get_document("custom_mode").get("mode", "components")
        
        # Calcular média por compra
        avg_per_purchase = user_stats['total_spent'] / user_stats['total_purchases'] if user_stats['total_purchases'] > 0 else 0
        
        # Datas
        first_date = datetime.fromtimestamp(user_stats["first_purchase"]).strftime("%d/%m/%Y") if user_stats.get("first_purchase") else "N/A"
        last_date = datetime.fromtimestamp(user_stats["last_purchase"]).strftime("%d/%m/%Y") if user_stats.get("last_purchase") else "N/A"
        
        # Produtos mais comprados
        products_bought = user_stats.get("products_bought", {})
        products_text = ""
        if products_bought:
            top_products = sorted(
                products_bought.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:3]
            
            for product_id, data in top_products:
                products_text += f"{emoji.star} **{data['name']}**\n"
                products_text += f"  {data['count']}x | R$ {data['spent']:.2f}\n"
        
        # Histórico recente
        history_text = ""
        if purchases:
            for purchase in purchases[:5]:
                date = datetime.fromtimestamp(purchase["timestamp"]).strftime("%d/%m %H:%M")
                product_name = purchase.get("product", {}).get("name", "Produto")
                quantity = purchase.get("quantity", 1)
                price = purchase.get("pricing", {}).get("final_price", 0)
                
                history_text += f"`{date}` {product_name} ({quantity}x) - R$ {price:.2f}\n"
        
        # Calcular ranking
        all_purchases = PurchaseManager.get_all_purchases()
        user_rankings = {}
        
        for purchase in all_purchases:
            uid = purchase.get("user_id")
            if uid:
                if uid not in user_rankings:
                    user_rankings[uid] = {"spent": 0, "items": 0}
                user_rankings[uid]["spent"] += purchase.get("pricing", {}).get("final_price", 0)
                user_rankings[uid]["items"] += purchase.get("quantity", 0)
        
        # Posição por valor
        sorted_by_value = sorted(
            user_rankings.items(),
            key=lambda x: x[1]["spent"],
            reverse=True
        )
        value_position = None
        for i, (uid, _) in enumerate(sorted_by_value):
            if uid == str(target.id):
                value_position = i + 1
                break
        
        # Posição por quantidade
        sorted_by_qty = sorted(
            user_rankings.items(),
            key=lambda x: x[1]["items"],
            reverse=True
        )
        qty_position = None
        for i, (uid, _) in enumerate(sorted_by_qty):
            if uid == str(target.id):
                qty_position = i + 1
                break
        
        ranking_text = ""
        if value_position:
            ranking_text += f"{emoji.dollar} **{value_position}º** em valor gasto\n"
        if qty_position:
            ranking_text += f"{emoji.cardbox} **{qty_position}º** em quantidade comprada"
        
        # Verificar condecorações
        customers_data = db.get_document("loja_customers")
        decorations = customers_data.get("decorations", {}).get("roles", [])
        user_decorations = []
        
        for decoration in decorations:
            if user_stats["total_spent"] >= decoration.get("min_spent", 0):
                role = inter.guild.get_role(int(decoration.get("role_id", 0)))
                if role and role in target.roles:
                    user_decorations.append(f"• {role.mention} - {decoration.get('name')}")
        
        decorations_text = "\n".join(user_decorations) if user_decorations else ""
        
        # Verificar saldo (se sistema ativado)
        saldo_text = ""
        saldo_enabled = BalanceManager.is_enabled()
        if saldo_enabled:
            user_balance = BalanceManager.get_user_balance(target.id)
            user_saldo_data = BalanceManager.get_user_data(target.id)
            total_deposited = user_saldo_data.get("total_deposited", 0)
            total_used = user_saldo_data.get("total_used", 0)
            
            if user_balance > 0 or total_deposited > 0:
                saldo_text = (
                    f"{emoji.wallet} **Saldo Atual:** `R$ {user_balance:.2f}`\n"
                    f"{emoji.correct} **Total Depositado:** `R$ {total_deposited:.2f}`\n"
                    f"{emoji.cart} **Total Usado:** `R$ {total_used:.2f}`"
                )
        
        if mode == "components":
            # Modo Components v2
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            # Construir texto do container
            stats_text = (
                f"{emoji.dollar} **Total Gasto:** `R$ {user_stats['total_spent']:.2f}`\n"
                f"{emoji.cardbox} **Total de Itens:** `{user_stats['total_items']} itens`\n"
                f"{emoji.cart} **Total de Compras:** `{user_stats['total_purchases']} compras`\n"
                f"{emoji.chart} **Média por Compra:** `R$ {avg_per_purchase:.2f}`\n\n"
                f"{emoji.calendar} **Primeira Compra:** `{first_date}`\n"
                f"{emoji.calendar} **Última Compra:** `{last_date}`"
            )
            
            components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.member} Perfil de Compras\n-# Estatísticas de {target.mention}"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(stats_text),
                    **container_kwargs
                )
            ]
            
            # Adicionar produtos favoritos se houver
            if products_text:
                components.append(
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"## {emoji.star} Produtos Favoritos\n{products_text}"),
                        **container_kwargs
                    )
                )
            
            # Adicionar histórico se houver
            if history_text:
                components.append(
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"## {emoji.receipt} Compras Recentes\n{history_text}"),
                        **container_kwargs
                    )
                )
            
            # Adicionar ranking se houver
            if ranking_text:
                components.append(
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"## {emoji.king} Posição no Ranking\n{ranking_text}"),
                        **container_kwargs
                    )
                )
            
            # Adicionar condecorações se houver
            if decorations_text:
                components.append(
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"## {emoji.shield_star} Condecorações\n{decorations_text}"),
                        **container_kwargs
                    )
                )
            
            # Adicionar saldo se houver
            if saldo_text:
                components.append(
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"## {emoji.wallet} Saldo\n{saldo_text}"),
                        **container_kwargs
                    )
                )
            
            await inter.followup.send(components=components, ephemeral=True)
        else:
            # Modo Embed
            embed = disnake.Embed(
                title=f"{emoji.cart} Perfil de Compras",
                description=f"Estatísticas de {target.mention}",
                color=disnake.Color.from_rgb(0, 202, 164)
            )
            
            embed.set_thumbnail(url=target.display_avatar.url)
            
            embed.add_field(
                name=f"{emoji.dollar} Total Gasto",
                value=f"R$ {user_stats['total_spent']:.2f}",
                inline=True
            )
            
            embed.add_field(
                name=f"{emoji.cardbox} Total de Itens",
                value=f"{user_stats['total_items']} itens",
                inline=True
            )
            
            embed.add_field(
                name=f"{emoji.cart} Total de Compras",
                value=f"{user_stats['total_purchases']} compras",
                inline=True
            )
            
            embed.add_field(
                name=f"{emoji.chart} Média por Compra",
                value=f"R$ {avg_per_purchase:.2f}",
                inline=True
            )
            
            embed.add_field(
                name=f"{emoji.calendar} Primeira Compra",
                value=first_date,
                inline=True
            )
            
            embed.add_field(
                name=f"{emoji.calendar} Última Compra",
                value=last_date,
                inline=True
            )
            
            if products_text:
                embed.add_field(
                    name=f"{emoji.star} Produtos Favoritos",
                    value=products_text or "Nenhum",
                    inline=False
                )
            
            if history_text:
                embed.add_field(
                    name=f"{emoji.receipt} Compras Recentes",
                    value=history_text or "Nenhuma",
                    inline=False
                )
            
            if ranking_text:
                embed.add_field(
                    name=f"{emoji.king} Posição no Ranking",
                    value=ranking_text,
                    inline=False
                )
            
            if decorations_text:
                embed.add_field(
                    name=f"{emoji.shield_star} Condecorações",
                    value=decorations_text,
                    inline=False
                )
            
            if saldo_text:
                embed.add_field(
                    name=f"{emoji.wallet} Saldo",
                    value=saldo_text,
                    inline=False
                )
            
            embed.set_footer(
                text=f"ID: {target.id} | Cliente desde {first_date}"
            )
            
            await inter.followup.send(embed=embed, ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(PerfilCommand(bot))