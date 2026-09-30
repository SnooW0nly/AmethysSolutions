"""
Context menu para editar produto da loja
"""
import disnake
from disnake.ext import commands

from functions.database import database as db
from modules.loja.products.product.configurar import ConfigurarProduto
from functions.message import message, embed_message
from functions.perms import perms
from functions.emoji import emoji


class EditProductContextMenu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.message_command(name="Editar Produto")
    async def edit_product(self, inter: disnake.MessageInteraction):
        await embed_message.wait(inter, send=True)

        if not await perms.check(inter.user.id):
            return await inter.edit_original_response(
                content=f"{emoji.wrong} Você não tem permissão para usar este comando"
            )

        target_message_id = inter.target.id

        products = db.get_document("loja_products") or {}
        
        product_id_found = None
        
        # Procurar o produto pela message_id (converter para int para compatibilidade com bson.int64.Int64)
        for product_id, product_data in products.items():
            messages = product_data.get("messages", [])
            for msg in messages:
                msg_id = msg.get("message_id")
                try:
                    # Converter ambos para int para garantir comparação correta
                    if int(msg_id) == int(target_message_id):
                        product_id_found = product_id
                        break
                except Exception:
                    continue
            if product_id_found:
                break

        if product_id_found:
            mode = db.get_document("custom_mode").get("mode")
            panel_data = ConfigurarProduto.panel(inter, product_id_found)
            
            if mode == "embed":
                await inter.edit_original_response(content=None, **panel_data)
            else:
                await inter.edit_original_response(content=None, **panel_data)
        else:
            await inter.edit_original_response(
                content=f"{emoji.wrong} Esta mensagem não é um produto configurado."
            )


def setup(bot):
    bot.add_cog(EditProductContextMenu(bot))
