import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji
from functions.utils import utils
from functions.loja_products import get_product, get_products, save_products
from modules.loja.cart.stock_manager import StockManager
from .product.configurar import ConfigurarProduto
import copy


class DuplicateProductModal(disnake.ui.Modal):
    """Modal para confirmar duplicação de estoque"""
    
    def __init__(self, source_product_id: str):
        self.source_product_id = source_product_id
        
        components = [
            disnake.ui.Label(
                text="Duplicar estoque?",
                component=disnake.ui.StringSelect(
                    placeholder="Você deseja duplicar os estoques também?",
                    custom_id="duplicate_stock",
                    required=True,
                    options=[
                        disnake.SelectOption(
                            label="Sim",
                            description="Duplicar o estoque junto com o produto",
                            value="yes",
                            emoji=emoji.correct,
                            default=True,
                        ),
                        disnake.SelectOption(
                            label="Não",
                            description="Apenas duplicar o produto, sem estoque",
                            value="no",
                            emoji=emoji.wrong,
                        ),
                    ],
                ),
                description="Selecione se deseja duplicar o estoque do produto original",
            ),
        ]
        
        super().__init__(title="Duplicar Produto", components=components, custom_id="duplicate_product_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        
        valores = inter.resolved_values
        
        duplicate_stock_value = valores.get("duplicate_stock", "")
        if isinstance(duplicate_stock_value, (list, tuple)):
            duplicate_stock = duplicate_stock_value[0] if duplicate_stock_value else "yes"
        else:
            duplicate_stock = duplicate_stock_value or "yes"
        
        duplicate_stock = duplicate_stock.lower() == "yes"
        
        # Obter produto original
        products = get_products()
        source_product = products.get(self.source_product_id)
        
        if not source_product:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Produto original não encontrado.")
                )
            ])
            return
        
        # Gerar novo ID para o produto duplicado
        new_product_id = utils.gerar_id()
        
        # Garantir que o ID é único
        while new_product_id in products:
            new_product_id = utils.gerar_id()
        
        # Fazer deep copy do produto
        duplicated_product = copy.deepcopy(source_product)
        
        # Atualizar informações do produto duplicado
        duplicated_product["id"] = new_product_id
        duplicated_product["name"] = f"{source_product.get('name', 'Produto')} (Cópia)"
        
        info = duplicated_product.get("info", {})
        info["created_at"] = int(disnake.utils.utcnow().timestamp())
        info["updated_at"] = int(disnake.utils.utcnow().timestamp())
        info["purchasesIds"] = []
        info["total_paid"] = 0
        duplicated_product["info"] = info
        
        # Limpar mensagens do produto duplicado
        duplicated_product["messages"] = []
        
        # Duplicar estoque se solicitado
        if duplicate_stock:
            # Obter estoque do produto original
            source_stock = StockManager._load_stock()
            source_product_stock = source_stock.get(self.source_product_id, {})
            
            if source_product_stock:
                # Copiar estoque para o novo produto
                stock_data = StockManager._load_stock()
                if new_product_id not in stock_data:
                    stock_data[new_product_id] = {}
                
                for campo_id, campo_stock in source_product_stock.items():
                    if isinstance(campo_stock, list):
                        # Copiar lista de itens
                        stock_data[new_product_id][campo_id] = campo_stock.copy()
                    elif isinstance(campo_stock, dict):
                        # Copiar dicionário
                        stock_data[new_product_id][campo_id] = campo_stock.copy()
                
                StockManager._save_stock(stock_data)
        
        # Salvar produto duplicado
        products[new_product_id] = duplicated_product
        save_products(products)
        
        # Retornar ao painel de gerenciar produtos
        # Obter o cog do bot para acessar o método panel
        from .cog import GerenciarProdutos
        # Buscar o cog já carregado no bot
        cog = None
        for loaded_cog in inter.client.cogs.values():
            if isinstance(loaded_cog, GerenciarProdutos):
                cog = loaded_cog
                break
        
        if not cog:
            # Se não encontrou, criar uma instância temporária
            cog = GerenciarProdutos(inter.client)
        
        panel_data = cog.panel(inter)
        
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))


def setup(bot: commands.Bot):
    # Este arquivo não precisa de cog, pois o modal é usado pelo cog de produtos
    pass

