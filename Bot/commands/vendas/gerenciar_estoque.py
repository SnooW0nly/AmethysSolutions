import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms
from functions.utils import utils


class GerenciarEstoqueCommand(commands.Cog):
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

    async def field_autocomplete(self, inter: disnake.ApplicationCommandInteraction, string: str):
        """Autocomplete para campos do produto selecionado"""
        products = db.get_document("loja_products") or {}
        produto_id = inter.options.get("produto") or inter.filled_options.get("produto", "")
        product = products.get(str(produto_id)) if produto_id else None

        if not product:
            # Sem produto selecionado ainda — retornar todos os campos de todos os produtos
            choices = []
            seen = set()
            for p in products.values():
                if not isinstance(p, dict):
                    continue
                for field_id, field_data in (p.get("campos") or {}).items():
                    if not isinstance(field_data, dict):
                        continue
                    name = field_data.get("name", "Sem nome")
                    key = f"{field_id}:{name}"
                    if key not in seen and string.lower() in name.lower():
                        seen.add(key)
                        choices.append(disnake.OptionChoice(name=name[:100], value=str(field_id)))
                    if len(choices) >= 25:
                        return choices
            return choices

        choices = []
        for field_id, field_data in (product.get("campos") or {}).items():
            if not isinstance(field_data, dict):
                continue
            name = field_data.get("name", "Sem nome")
            if string.lower() in name.lower():
                choices.append(disnake.OptionChoice(name=name[:100], value=str(field_id)))
            if len(choices) >= 25:
                break

        return choices

    @commands.slash_command(
        name="gerenciar_estoque",
        description="Abre o painel de estoque de um campo de produto",
        guild_ids=[utils.obter_server_principal()],
        default_member_permissions=disnake.Permissions(administrator=True),
    )
    async def gerenciar_estoque(
        self,
        inter: disnake.ApplicationCommandInteraction,
        produto: str = commands.Param(
            description="Produto a gerenciar",
            autocomplete=product_autocomplete,
        ),
        campo: str = commands.Param(
            description="Campo do produto cujo estoque será aberto",
            autocomplete=field_autocomplete,
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
        product = products.get(produto)
        if not product:
            await inter.followup.send(
                f"{emoji.wrong} Produto não encontrado!", ephemeral=True
            )
            return

        campos = product.get("campos") or {}
        if campo not in campos:
            await inter.followup.send(
                f"{emoji.wrong} Campo não encontrado neste produto!", ephemeral=True
            )
            return

        mode = db.get_document("custom_mode").get("mode")

        from modules.loja.products.product.campos.fields.estoque.visualizar import panel as stock_panel

        panel_data = stock_panel(inter, produto, campo)

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
    bot.add_cog(GerenciarEstoqueCommand(bot))