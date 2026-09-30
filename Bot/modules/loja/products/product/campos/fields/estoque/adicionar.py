import disnake
import asyncio

from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji
from modules.loja.cart.stock_manager import StockManager
from modules.loja.preferences.notificar_restock import notify_restock

KEY_PRODUCTS = "loja_products"


class AdicionarEstoqueModal(disnake.ui.Modal):
    def __init__(self, product_id: str, field_id: str):
        self.product_id = product_id
        self.field_id = field_id

        components = [
            disnake.ui.Label(
                text="Estoque (um por linha)",
                component=disnake.ui.TextInput(
                    custom_id="stock_lines",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Cole/insira itens, um por linha",
                    required=True,
                    max_length=4000,
                ),
                description="Máximo de 1000 itens por vez.",
            )
        ]
        super().__init__(title="Adicionar Estoque", components=components, custom_id=f"stock_add_modal:{product_id}:{field_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        valores = inter.resolved_values
        stock_text = (valores.get("stock_lines") or "").strip()
        items = [line.strip() for line in stock_text.split("\n") if line.strip()]
        
        # Limitar cada item a 2000 caracteres
        MAX_ITEM_LENGTH = 2000
        items = [item[:MAX_ITEM_LENGTH] if len(item) > MAX_ITEM_LENGTH else item for item in items]
        
        # Validar quantidade de itens
        MAX_ITEMS_PER_ADD = 1000
        if not items:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Nenhum item válido informado.")
                )
            ])
            return
        if len(items) > MAX_ITEMS_PER_ADD:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Máximo de {MAX_ITEMS_PER_ADD} itens por vez. Você tentou adicionar {len(items)} itens.")
                )
            ])
            return

        # Adicionar itens ao estoque centralizado
        try:
            should_notify = StockManager.add_stock_items(self.product_id, self.field_id, items)
            
            # Se precisa notificar via StockManager, chamar função assíncrona
            if should_notify:
                bot = inter.client
                if bot:
                    asyncio.create_task(
                        StockManager._notify_stock_available(self.product_id, self.field_id, bot)
                    )
            
            # Notificar canal de restock configurado nas preferências
            asyncio.create_task(
                notify_restock(inter.client, self.product_id, self.field_id, len(items))
            )
        except Exception as e:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Erro ao adicionar estoque: {str(e)}")
                )
            ])
            return

        # Atualizar timestamp no products
        products = db.get_document(KEY_PRODUCTS)
        product = (products or {}).get(self.product_id) or {}
        campos = product.get("campos") or {}
        field = campos.get(self.field_id) or {}

        # Desativar estoque infinito ao adicionar estoque normal
        stock_info = field.get("stock_info") or {}
        if field.get("infinite_stock", {}).get("enabled", False):
            field["infinite_stock"] = {
                "enabled": False,
                "disabled_at": int(disnake.utils.utcnow().timestamp())
            }
            stock_info["is_infinite"] = False
        
        stock_info["last"] = int(disnake.utils.utcnow().timestamp())
        field["stock_info"] = stock_info

        field["updated_at"] = int(disnake.utils.utcnow().timestamp())
        campos[self.field_id] = field
        product["campos"] = campos
        info = product.get("info") or {}
        info["updated_at"] = int(disnake.utils.utcnow().timestamp())
        product["info"] = info
        products[self.product_id] = product
        db.save_document(KEY_PRODUCTS, products)
        
        # Sincronizar silenciosamente todas as mensagens do produto
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(inter.client, self.product_id)

        # Return to stock panel
        from .visualizar import panel as stock_panel
        panel_data = stock_panel(inter, self.product_id, self.field_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)
class AdicionarEstoqueInfinitoModal(disnake.ui.Modal):
    def __init__(self, product_id: str, field_id: str):
        self.product_id = product_id
        self.field_id = field_id

        # Verificar se já existe valor configurado
        products = db.get_document(KEY_PRODUCTS) or {}
        product = products.get(product_id) or {}
        field = (product.get("campos") or {}).get(field_id) or {}
        current_value = field.get("infinite_stock", {}).get("value", "")

        components = [
            disnake.ui.TextInput(
                label="Valor/Informação entregue",
                custom_id="infinite_value",
                style=disnake.TextInputStyle.paragraph,
                placeholder="Ex.: Código de ativação, link de acesso, instruções, etc.",
                required=True,
                max_length=2000,
                value=current_value,  # Pré-preencher com valor atual se existir
            ),
        ]
        super().__init__(title="Configurar Estoque Infinito", components=components, custom_id=f"stock_add_infinite_modal:{product_id}:{field_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        valores = inter.resolved_values
        value_text = (valores.get("infinite_value") or "").strip()
        
        if not value_text:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Você deve fornecer um valor para o estoque infinito.")
                )
            ])
            return

        # Atualizar campo para estoque infinito
        products = db.get_document(KEY_PRODUCTS) or {}
        product = products.get(self.product_id) or {}
        campos = product.get("campos") or {}
        field = campos.get(self.field_id) or {}

        # Configurar estoque infinito
        field["infinite_stock"] = {
            "enabled": True,
            "value": value_text,
            "configured_at": int(disnake.utils.utcnow().timestamp())
        }
        
        # Limpar estoque normal se existir (tanto no field quanto no StockManager)
        if "stock" in field:
            del field["stock"]
        
        # Limpar estoque do StockManager centralizado
        stock = StockManager._load_stock()
        if self.product_id in stock and self.field_id in stock[self.product_id]:
            stock[self.product_id][self.field_id] = []
            StockManager._save_stock(stock)
        
        stock_info = field.get("stock_info") or {}
        stock_info["is_infinite"] = True
        stock_info["last"] = int(disnake.utils.utcnow().timestamp())
        field["stock_info"] = stock_info

        field["updated_at"] = int(disnake.utils.utcnow().timestamp())
        campos[self.field_id] = field
        product["campos"] = campos
        info = product.get("info") or {}
        info["updated_at"] = int(disnake.utils.utcnow().timestamp())
        product["info"] = info
        products[self.product_id] = product
        db.save_document(KEY_PRODUCTS, products)
        
        # Sincronizar silenciosamente todas as mensagens do produto
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(inter.client, self.product_id)

        # Return to stock panel
        from .visualizar import panel as stock_panel
        panel_data = stock_panel(inter, self.product_id, self.field_id)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel_data)
        else:
            await inter.edit_original_message(**panel_data)


class PegarItensEstoqueModal(disnake.ui.Modal):
    def __init__(self, product_id: str, field_id: str):
        self.product_id = product_id
        self.field_id = field_id

        # Verificar estoque disponível
        available_stock = StockManager.get_available_stock(product_id, field_id)
        
        components = [
            disnake.ui.TextInput(
                label="Quantidade de itens",
                custom_id="quantity",
                style=disnake.TextInputStyle.short,
                placeholder=f"Digite a quantidade (disponível: {available_stock if available_stock != 999999 else 'Infinito'})",
                required=True,
                max_length=10,
                value="1",  # Valor padrão
            ),
        ]
        super().__init__(title="Pegar Itens do Estoque", components=components, custom_id=f"stock_get_items_modal:{product_id}:{field_id}")

    async def callback(self, inter: disnake.ModalInteraction):
        # Check mode first to use appropriate wait function
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter)
        valores = inter.resolved_values
        quantity_text = (valores.get("quantity") or "").strip()
        
        try:
            quantity = int(quantity_text)
            if quantity <= 0:
                raise ValueError("Quantidade deve ser maior que zero")
        except ValueError:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Quantidade inválida! Digite um número inteiro positivo.")
                )
            ])
            return
        
        # Verificar se é estoque infinito
        products = db.get_document(KEY_PRODUCTS) or {}
        product = (products or {}).get(self.product_id) or {}
        field = (product.get("campos") or {}).get(self.field_id) or {}
        is_infinite = field.get("infinite_stock", {}).get("enabled", False)
        
        if not is_infinite:
            # Verificar estoque disponível
            available_stock = StockManager.get_available_stock(self.product_id, self.field_id)
            if quantity > available_stock:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.wrong} Estoque insuficiente! Disponível: `{available_stock}`, solicitado: `{quantity}`.")
                    )
                ])
                return
        
        # Retirar itens do estoque centralizado
        items = StockManager.get_stock_items(self.product_id, self.field_id, quantity)
        
        if items is None or len(items) == 0:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Não há estoque suficiente neste campo.")
                )
            ])
            return
        
        # Atualizar timestamp no products
        stock_info = field.get("stock_info") or {}
        stock_info["last"] = int(disnake.utils.utcnow().timestamp())
        field["stock_info"] = stock_info
        field["updated_at"] = int(disnake.utils.utcnow().timestamp())
        campos = product.get("campos") or {}
        campos[self.field_id] = field
        product["campos"] = campos
        info = product.get("info") or {}
        info["updated_at"] = int(disnake.utils.utcnow().timestamp())
        product["info"] = info
        products[self.product_id] = product
        db.save_document(KEY_PRODUCTS, products)
        
        # Sincronizar silenciosamente todas as mensagens do produto
        from modules.loja.products.product.edit import sync_product_messages_silently
        await sync_product_messages_silently(inter.client, self.product_id)
        
        # Formatar mensagem com os itens retirados
        if len(items) <= 10:
            # Mostrar todos os itens se forem 10 ou menos
            items_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(items)])
        else:
            # Mostrar primeiros 10 e indicar quantos mais há
            items_text = "\n".join([f"{i+1}. {item}" for i, item in enumerate(items[:10])])
            items_text += f"\n\n... e mais {len(items) - 10} item(s)"
        
        await inter.edit_original_message(components=[
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.correct} {len(items)} item(s) retirado(s) do estoque:\n\n{items_text}"
                )
            )
        ])
        
        # Atualizar o painel após retirar os itens
        from .visualizar import panel as stock_panel
        mode = db.get_document("custom_mode").get("mode")
        await (embed_message if mode == "embed" else message).wait(inter, send=False)
        panel_data = stock_panel(inter, self.product_id, self.field_id)
        if mode == "embed":
            await inter.edit_original_message(**panel_data)
        else:
            await inter.edit_original_message(**panel_data)