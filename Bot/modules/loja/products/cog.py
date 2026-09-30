from disnake.ext import commands, tasks
import disnake

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from functions.utils import utils
from modules.loja.cart.stock_manager import StockManager

class GerenciarProdutos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def gerar_dropdown_produtos(self, products: dict, page: int = 0, duplicar_mode: bool = False) -> list:
        """Gera dropdowns paginados para produtos (25 por página)
        
        Args:
            products: Dicionário de produtos
            page: Número da página (não usado mais, mantido para compatibilidade)
            duplicar_mode: Se True, usa custom_id para duplicação
        """
        if not products:
            custom_id = "Loja_DuplicarProduto_Select" if duplicar_mode else "Loja_Produtos_Select"
            return [disnake.ui.StringSelect(
                placeholder="Nenhum produto encontrado",
                options=[disnake.SelectOption(label="Nenhum produto encontrado", value="disabled")],
                custom_id=custom_id,
                disabled=True
            )]
        
        # Converter para lista e ordenar por nome
        product_list = sorted(products.items(), key=lambda x: x[1].get("name", "").lower())
        total_products = len(product_list)
        
        # Calcular paginação
        items_per_page = 25
        total_pages = (total_products + items_per_page - 1) // items_per_page
        
        # Se só tem uma página, retornar dropdown único
        if total_pages == 1:
            options = []
            for product_id, product in product_list:
                product_name = product.get("name", "Sem nome")
                if len(product_name) > 80:
                    product_name = product_name[:77] + "..."
                
                campos_count = len(product.get("campos", {}))
                cupons_count = len(product.get("cupons", {}))
                description = f'Campos: {campos_count} | Cupons: {cupons_count}'
                
                if len(description) > 100:
                    description = description[:97] + "..."
                
                options.append(disnake.SelectOption(
                    label=product_name,
                    value=product_id,
                    description=description
                ))
            
            custom_id = "Loja_DuplicarProduto_Select" if duplicar_mode else "Loja_Produtos_Select"
            return [disnake.ui.StringSelect(
                placeholder=f"[{total_products}] Selecione um produto",
                options=options,
                custom_id=custom_id
            )]
        
        # Múltiplas páginas - criar dropdowns
        dropdowns = []
        for page_num in range(total_pages):
            start_idx = page_num * items_per_page
            end_idx = min(start_idx + items_per_page, total_products)
            page_products = product_list[start_idx:end_idx]
            
            options = []
            for product_id, product in page_products:
                product_name = product.get("name", "Sem nome")
                if len(product_name) > 80:
                    product_name = product_name[:77] + "..."
                
                campos_count = len(product.get("campos", {}))
                cupons_count = len(product.get("cupons", {}))
                description = f'Campos: {campos_count} | Cupons: {cupons_count}'
                
                if len(description) > 100:
                    description = description[:97] + "..."
                
                options.append(disnake.SelectOption(
                    label=product_name,
                    value=product_id,
                    description=description
                ))
            
            # Placeholder indicando página e intervalo
            placeholder = f"[Página {page_num + 1}/{total_pages}] Produtos {start_idx + 1}-{end_idx}"
            
            custom_id_prefix = "Loja_DuplicarProduto_Select" if duplicar_mode else "Loja_Produtos_Select"
            dropdowns.append(disnake.ui.StringSelect(
                placeholder=placeholder,
                options=options,
                custom_id=f"{custom_id_prefix}_Page{page_num}"
            ))
        
        return dropdowns

    def panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return self._panel_embed(inter)
        return self._panel_components(inter)

    def _panel_components(self, inter: disnake.MessageInteraction) -> dict:
        products = db.get_document("loja_products") or {}
        dropdowns = self.gerar_dropdown_produtos(products)

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        # Criar ActionRows para os dropdowns
        dropdown_rows = [disnake.ui.ActionRow(dropdown) for dropdown in dropdowns]
        
        # Adicionar dropdowns e botão ao container
        container_items = [
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > **Gerenciar Produtos**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"Selecione um produto abaixo para gerenciá-lo.\nSe deseja criar um produto, clique no botão **Criar Novo Produto**."),
            disnake.ui.Separator(),
        ]
        
        # Adicionar todos os dropdowns
        container_items.extend(dropdown_rows)
        
        # Adicionar botões de criar e duplicar
        container_items.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Novo Produto", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Loja_CriarProduto"),
                disnake.ui.Button(label="Duplicar Produto", style=disnake.ButtonStyle.blurple, emoji=emoji.reload, custom_id="Loja_DuplicarProduto"),
            )
        )

        return {"components": [
            disnake.ui.Container(*container_items, **container_kwargs),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Loja")),
        ]}

    def _panel_embed(self, inter: disnake.MessageInteraction) -> dict:
        products = db.get_document("loja_products") or {}
        dropdowns = self.gerar_dropdown_produtos(products)

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        embed_kwargs = {}
        if primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

        embed = disnake.Embed(
            description=f"-# Painel > Loja > **Gerenciar Produtos**\n\nSelecione uma das opções abaixo para gerenciar os produtos da sua loja.\nSe desejar adicionar um novo produto, clique no botão **Adicionar Produto**.",
            **embed_kwargs
        )

        # Criar componentes com múltiplos dropdowns
        components = []
        for dropdown in dropdowns:
            components.append(disnake.ui.ActionRow(dropdown))
        
        components.extend([
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Novo Produto", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Loja_CriarProduto"),
                disnake.ui.Button(label="Duplicar Produto", style=disnake.ButtonStyle.blurple, emoji=emoji.reload, custom_id="Loja_DuplicarProduto"),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Loja")),
        ])
        
        return {"embed": embed, "components": components}

    def _panel_duplicar_produto(self, inter: disnake.MessageInteraction) -> dict:
        """Painel para selecionar produto a duplicar"""
        products = db.get_document("loja_products") or {}
        dropdowns = self.gerar_dropdown_produtos(products, duplicar_mode=True)

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        # Criar ActionRows para os dropdowns
        dropdown_rows = [disnake.ui.ActionRow(dropdown) for dropdown in dropdowns]
        
        # Adicionar dropdowns e botão ao container
        container_items = [
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > **Gerenciar Produtos** > **Duplicar Produto**"),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(f"Selecione um produto abaixo para duplicá-lo."),
            disnake.ui.Separator(),
        ]
        
        # Adicionar todos os dropdowns
        container_items.extend(dropdown_rows)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed_kwargs = {}
            if primary_color_hex:
                embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
            
            embed = disnake.Embed(
                description=f"-# Painel > Loja > **Gerenciar Produtos** > **Duplicar Produto**\n\nSelecione um produto abaixo para duplicá-lo.",
                **embed_kwargs
            )
            
            components = []
            for dropdown in dropdowns:
                components.append(disnake.ui.ActionRow(dropdown))
            
            components.append(disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Produtos")))
            
            return {"embed": embed, "components": components}

        return {"components": [
            disnake.ui.Container(*container_items, **container_kwargs),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Produtos")),
        ]}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Produtos":
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)

            panel_data = self.panel(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_DuplicarProduto":
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)

            panel_data = self._panel_duplicar_produto(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Validar mensagens salvas na database
        elif inter.component.custom_id == "Loja_Produtos_ValidarMensagens":
            await inter.response.defer(ephemeral=True)
            products = db.get_document("loja_products") or {}
            total_checked = 0
            total_removed = 0
            changed = False
            for product_id, p in products.items():
                msgs = p.get("messages") or []
                if not isinstance(msgs, list) or not msgs:
                    continue
                new_msgs = []
                for m in msgs:
                    try:
                        msg_guild_id = m.get("guild_id")
                        msg_channel_id = m.get("channel_id")
                        msg_id = m.get("message_id")
                        if not (msg_channel_id and msg_id):
                            # inválido
                            total_removed += 1
                            continue
                        # validar apenas mensagens deste servidor para evitar falsas remoções
                        if msg_guild_id and msg_guild_id != inter.guild.id:
                            new_msgs.append(m)
                            continue
                        channel = inter.guild.get_channel(int(msg_channel_id))
                        if channel is None:
                            total_removed += 1
                            continue
                        # tentar buscar a mensagem
                        try:
                            await channel.fetch_message(int(msg_id))
                            new_msgs.append(m)  # existe
                        except disnake.NotFound:
                            total_removed += 1
                        except (disnake.Forbidden, disnake.HTTPException):
                            # sem permissão ou erro transitório: manter por segurança
                            new_msgs.append(m)
                    finally:
                        total_checked += 1
                if len(new_msgs) != len(msgs):
                    products[product_id]["messages"] = new_msgs
                    changed = True
            if changed:
                db.save_document("loja_products", products)

            # construir retorno visual
            color_data = db.get_document("custom_colors") or {}
            primary_color_hex = color_data.get("primary")
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

            result_container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Loja > **Validar Mensagens**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"**Mensagens verificadas:** `{total_checked}`\n"
                    f"**Removidas da database:** `{total_removed}`\n"
                    f"**Documento:** `loja_products`"
                ),
                **container_kwargs
            )
            await inter.followup.send(components=[result_container], ephemeral=True, flags=disnake.MessageFlags(is_components_v2=True))

    @tasks.loop(hours=1)
    async def _auto_validate_messages(self):
        products = db.get_document("loja_products") or {}
        changed = False
        for product_id, p in products.items():
            msgs = p.get("messages") or []
            if not isinstance(msgs, list) or not msgs:
                continue
            new_msgs = []
            for m in msgs:
                try:
                    gid = m.get("guild_id")
                    cid = m.get("channel_id")
                    mid = m.get("message_id")
                    if not (cid and mid and gid):
                        continue
                    guild = self.bot.get_guild(int(gid)) if gid else None
                    if guild is None:
                        continue
                    channel = guild.get_channel(int(cid)) if cid else None
                    if channel is None:
                        continue
                    try:
                        await channel.fetch_message(int(mid))
                        new_msgs.append(m)
                    except disnake.NotFound:
                        pass
                    except (disnake.Forbidden, disnake.HTTPException):
                        new_msgs.append(m)
                except Exception:
                    pass
            if len(new_msgs) != len(msgs):
                products[product_id]["messages"] = new_msgs
                changed = True
        if changed:
            db.save_document("loja_products", products)

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        # Handler para dropdowns paginados de produtos normais
        if inter.component.custom_id.startswith("Loja_Produtos_Select"):
            product_id = inter.values[0]
            if product_id == "disabled":
                await inter.response.defer()
                return
            
            # Importar e chamar o painel de configuração
            from .product.configurar import ConfigurarProduto
            mode = db.get_document("custom_mode").get("mode")
            panel_data = ConfigurarProduto.panel(inter, product_id)
            
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel_data)
        
        # Handler para dropdown de duplicar produto
        elif inter.component.custom_id.startswith("Loja_DuplicarProduto_Select"):
            product_id = inter.values[0]
            if product_id == "disabled":
                await inter.response.defer()
                return
            
            # Abrir modal perguntando se quer duplicar estoque
            from .duplicate import DuplicateProductModal
            await inter.response.send_modal(DuplicateProductModal(product_id))

    @_auto_validate_messages.before_loop
    async def _before_auto_validate_messages(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._auto_validate_messages.is_running():
            self._auto_validate_messages.start()

    def cog_unload(self):
        if self._auto_validate_messages.is_running():
            self._auto_validate_messages.cancel()

def setup(bot: commands.Bot):
    bot.add_cog(GerenciarProdutos(bot))