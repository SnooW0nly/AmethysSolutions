import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms
from functions.utils import utils


class GerenciarProdutoCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def product_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str):
        """Autocomplete para produtos"""
        products = db.get_document("loja_products") or {}
        string = string.lower()
        choices = []

        for product_id, product_data in products.items():
            if not isinstance(product_data, dict):
                continue
            name = product_data.get("name", "Sem nome")
            if string in name.lower():
                choices.append(disnake.OptionChoice(name=name[:100], value=str(product_id)))
            if len(choices) >= 25:
                break

        return choices

    @commands.slash_command(
        name="gerenciar_produto",
        description="Abre o painel de configuração de um produto diretamente",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(administrator=True),
    )
    async def gerenciar_produto(
        self,
        inter: disnake.ApplicationCommandInteraction,
        produto: str = commands.Param(
            description="Produto a gerenciar",
            autocomplete=product_autocomplete,
        ),
    ):
        if not await perms.check(inter.author.id):
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando!",
                ephemeral=True,
            )
            return

        await inter.response.defer(ephemeral=True)

        products = db.get_document("loja_products") or {}
        if produto not in products:
            await inter.followup.send(
                f"{emoji.wrong} Produto não encontrado!", ephemeral=True
            )
            return

        mode = db.get_document("custom_mode").get("mode")

        from modules.loja.products.product.configurar import ConfigurarProduto

        panel_data = ConfigurarProduto.panel(inter, produto)

        if mode == "embed":
            await inter.followup.send(
                content=None,
                ephemeral=True,
                **panel_data,
            )
        else:
            await inter.followup.send(
                ephemeral=True,
                flags=disnake.MessageFlags(is_components_v2=True),
                **panel_data,
            )


def setup(bot: commands.Bot):
    bot.add_cog(GerenciarProdutoCommand(bot))