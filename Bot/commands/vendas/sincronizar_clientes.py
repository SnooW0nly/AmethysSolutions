import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms
from functions.utils import utils


class SincronizarClientesCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.slash_command(
        name="sincronizar_clientes",
        description="Sincroniza manualmente os cargos de clientes",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(administrator=True)
    )
    async def sincronizar_clientes(self, inter: disnake.ApplicationCommandInteraction):
        # Verificar permissões
        if not await perms.check(inter.author.id):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando!",
                ephemeral=True
            )
            return
        
        await inter.response.defer(ephemeral=True)
        
        # Obter cog de clientes
        clientes_cog = self.bot.get_cog("ClientesSystem")
        if not clientes_cog:
            await inter.followup.send(
                f"{emoji.wrong} Sistema de clientes não está carregado!",
                ephemeral=True
            )
            return
        
        # Executar sincronização
        try:
            await clientes_cog.sync_all_customers()
            
            # Obter estatísticas
            from modules.loja.cart.purchase_manager import PurchaseManager
            stats = PurchaseManager.get_statistics()
            
            customers_data = db.get_document("loja_customers")
            decorations = customers_data.get("decorations", {}).get("roles", [])
            base_role = db.get_document("cargos").get("cargo_cliente")
            
            embed = disnake.Embed(
                title=f"{emoji.correct} Sincronização Concluída!",
                description="Os cargos de clientes foram atualizados com sucesso.",
                color=disnake.Color.green()
            )
            
            embed.add_field(
                name="Estatísticas",
                value=(
                    f"Clientes únicos: **{stats.get('unique_customers', 0)}**\n"
                    f"Total de vendas: **{stats.get('total_purchases', 0)}**\n"
                    f"Receita total: **R$ {stats.get('total_revenue', 0):.2f}**"
                ),
                inline=False
            )
            
            if decorations:
                decorations_text = f"Condecorações ativas: **{len(decorations)}**"
            else:
                decorations_text = "Nenhuma condecoração configurada"
            
            embed.add_field(
                name="🎖️ Condecorações",
                value=decorations_text,
                inline=True
            )
            
            if base_role:
                role = inter.guild.get_role(int(base_role))
                if role:
                    embed.add_field(
                        name="👥 Cargo Base",
                        value=role.mention,
                        inline=True
                    )
            
            embed.set_footer(text="A sincronização automática ocorre a cada 5 minutos")
            
            await inter.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao sincronizar: {e}",
                ephemeral=True
            )


def setup(bot: commands.Bot):
    bot.add_cog(SincronizarClientesCommand(bot))