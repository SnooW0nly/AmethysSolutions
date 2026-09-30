import disnake

from disnake.ext import commands
from functions.database import database as db
from functions.message import message, embed_message
from .visualizar import panel as stock_panel, export_stock_file
from .adicionar import AdicionarEstoqueModal, AdicionarEstoqueInfinitoModal, PegarItensEstoqueModal
from .limpar import clear_stock
from .gerenciar import (
    panel as gerenciar_panel,
    RemoverItemModal,
    BuscarEstoqueModal,
    remove_duplicates,
    _state_clear,
)
from modules.loja.cart.stock_manager import StockManager


class EstoqueCampoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Tracking de uploads pendentes: user_id -> (product_id, field_id, timestamp)
        self.pending_uploads = {}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""
        if custom_id.startswith("Loja_EstoqueCampo:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await (embed_message if mode == "embed" else message).wait(inter, send=False)
                except:
                    pass  # Another listener already responded
            panel_data = stock_panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(**panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_EstoqueCampo_Voltar:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await (embed_message if mode == "embed" else message).wait(inter, send=False)
                except:
                    pass  # Another listener already responded
            from ..configurar import ConfigurarCampo
            panel_data = ConfigurarCampo.panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_Estoque_Add:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            await inter.response.send_modal(AdicionarEstoqueModal(product_id, field_id))
            return

        if custom_id.startswith("Loja_Estoque_AddInfinite:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            await inter.response.send_modal(AdicionarEstoqueInfinitoModal(product_id, field_id))
            return

        if custom_id.startswith("Loja_Estoque_Clear:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            
            # Verificar se é estoque infinito antes de limpar
            products = db.get_document("loja_products")
            product = (products or {}).get(product_id) or {}
            field = product.get("campos", {}).get(field_id, {})
            
            if field.get("infinite_stock", {}).get("enabled"):
                # Se for estoque infinito, apenas remove a configuração
                del field["infinite_stock"]
                
                # Atualizar stock_info
                stock_info = field.get("stock_info") or {}
                stock_info["is_infinite"] = False
                stock_info["last"] = int(disnake.utils.utcnow().timestamp())
                field["stock_info"] = stock_info
                
                # Salvar alterações
                product["campos"][field_id] = field
                products[product_id] = product
                db.save_document("loja_products", products)
                
                # Sincronizar silenciosamente todas as mensagens do produto
                from modules.loja.products.product.edit import sync_product_messages_silently
                await sync_product_messages_silently(inter.client, product_id)
            else:
                # Se não for infinito, limpa normalmente
                clear_stock(product_id, field_id)
                
                # Sincronizar silenciosamente todas as mensagens do produto
                from modules.loja.products.product.edit import sync_product_messages_silently
                await sync_product_messages_silently(inter.client, product_id)
            
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await (embed_message if mode == "embed" else message).wait(inter, send=False)
                except:
                    pass  # Another listener already responded
            panel_data = stock_panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(**panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        elif custom_id.startswith("Loja_Estoque_View:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            
            from functions.emoji import emoji
            from functions.loja_products import get_product
            
            # Verificar se é estoque infinito
            product = get_product(product_id)
            field = (product.get("campos") or {}).get(field_id) or {}
            is_infinite = field.get("infinite_stock", {}).get("enabled", False)
            
            if is_infinite:
                # Mostrar valor do estoque infinito
                infinite_value = field.get("infinite_stock", {}).get("value", "Não configurado")
                await inter.response.send_message(
                    f"{emoji.correct} **Estoque Infinito Configurado:**\n```{infinite_value}```",
                    ephemeral=True
                )
            else:
                # Verificar estoque normal
                path = export_stock_file(product_id, field_id)
                if not path:
                    await inter.response.send_message(
                        f"{emoji.wrong} Nenhum item no estoque.",
                        ephemeral=True
                    )
                else:
                    await inter.response.send_message(
                        content=f"{emoji.correct} Aqui está o arquivo com todos os itens do estoque:",
                        files=[disnake.File(fp=path)],
                        ephemeral=True
                    )
                    try:
                        import os
                        os.remove(path)
                    except Exception:
                        pass
            return

        if custom_id.startswith("Loja_Estoque_Pegar:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            
            # Abrir modal para escolher quantidade
            await inter.response.send_modal(PegarItensEstoqueModal(product_id, field_id))
            return

        # ── Gerenciar Estoque ─────────────────────────────────────────────────

        if custom_id.startswith("Loja_Estoque_Gerenciar:"):
            # Botão principal — abre o painel de gerenciamento na página 0
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await (embed_message if mode == "embed" else message).wait(inter, send=False)
                except Exception:
                    pass
            panel_data = gerenciar_panel(inter, product_id, field_id, page=0)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_Estoque_Gerenciar_Page:"):
            # Paginação — "Loja_Estoque_Gerenciar_Page:{product_id}:{field_id}:{page}"
            parts = custom_id.split(":")
            # parts: [prefix, product_id, field_id, page]
            product_id = parts[1]
            field_id = parts[2]
            page = int(parts[3]) if len(parts) > 3 else 0
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await (embed_message if mode == "embed" else message).wait(inter, send=False)
                except Exception:
                    pass
            panel_data = gerenciar_panel(inter, product_id, field_id, page=page)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_Estoque_Gerenciar_Remove:"):
            # "Loja_Estoque_Gerenciar_Remove:{product_id}:{field_id}:{page}"
            parts = custom_id.split(":")
            product_id = parts[1]
            field_id = parts[2]
            page = int(parts[3]) if len(parts) > 3 else 0
            await inter.response.send_modal(RemoverItemModal(product_id, field_id, page))
            return

        if custom_id.startswith("Loja_Estoque_Gerenciar_Dedup:"):
            # "Loja_Estoque_Gerenciar_Dedup:{product_id}:{field_id}"
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await (embed_message if mode == "embed" else message).wait(inter, send=False)
                except Exception:
                    pass

            from functions.emoji import emoji as _emoji
            removed = remove_duplicates(product_id, field_id)

            # Sincronizar silenciosamente
            from modules.loja.products.product.edit import sync_product_messages_silently
            await sync_product_messages_silently(inter.client, product_id)

            if removed == 0:
                result_text = f"{_emoji.information} Nenhuma duplicata encontrada no estoque."
            else:
                result_text = (
                    f"{_emoji.correct} **{removed}** item(s) duplicado(s) removido(s) com sucesso."
                )

            await inter.edit_original_message(components=[
                disnake.ui.Container(disnake.ui.TextDisplay(result_text))
            ])
            import asyncio as _asyncio
            await _asyncio.sleep(1.5)

            panel_data = gerenciar_panel(inter, product_id, field_id, page=0)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_Estoque_Gerenciar_Search:"):
            # "Loja_Estoque_Gerenciar_Search:{product_id}:{field_id}:{page}"
            parts = custom_id.split(":")
            product_id = parts[1]
            field_id = parts[2]
            page = int(parts[3]) if len(parts) > 3 else 0
            await inter.response.send_modal(BuscarEstoqueModal(product_id, field_id, page))
            return

        if custom_id.startswith("Loja_Estoque_Gerenciar_ClearSearch:"):
            # "Loja_Estoque_Gerenciar_ClearSearch:{product_id}:{field_id}"
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await (embed_message if mode == "embed" else message).wait(inter, send=False)
                except Exception:
                    pass
            _state_clear(inter.user.id, product_id, field_id)
            panel_data = gerenciar_panel(inter, product_id, field_id, page=0)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_Estoque_Gerenciar_Voltar:"):
            # "Loja_Estoque_Gerenciar_Voltar:{product_id}:{field_id}"
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            mode = db.get_document("custom_mode").get("mode")
            if not inter.response.is_done():
                try:
                    await (embed_message if mode == "embed" else message).wait(inter, send=False)
                except Exception:
                    pass
            _state_clear(inter.user.id, product_id, field_id)
            panel_data = stock_panel(inter, product_id, field_id)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data)
            return

        if custom_id.startswith("Loja_Estoque_Upload:"):
            _, rest = custom_id.split(":", 1)
            product_id, field_id = rest.split(":", 1)
            
            from functions.emoji import emoji
            from functions.loja_products import get_product
            from functions.text_utils import safe_textdisplay
            
            # Obter informações do produto e campo
            product = get_product(product_id)
            product_name = safe_textdisplay(product.get("name") or product_id, 50)
            campo = (product.get("campos") or {}).get(field_id) or {}
            campo_name = safe_textdisplay(campo.get("name") or field_id, 50)
            
            # Registrar upload pendente
            import time
            self.pending_uploads[inter.user.id] = {
                "product_id": product_id,
                "field_id": field_id,
                "timestamp": time.time()
            }
            
            # Tentar enviar DM
            try:
                dm_channel = await inter.user.create_dm()
                
                mode = db.get_document("custom_mode").get("mode")
                color_data = db.get_document("custom_colors")
                primary_color_hex = color_data.get("primary")
                
                if mode == "embed":
                    embed_kwargs = {}
                    if primary_color_hex:
                        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                    
                    embed = disnake.Embed(
                        description=(
                            f"-# {emoji.folder} **Upload de Estoque**\n\n"
                            f"-# Produto: **{product_name}**\n"
                            f"-# Campo: **{campo_name}**\n\n"
                            f"Por favor, envie um arquivo **.txt** com os itens de estoque.\n"
                            f"Cada item deve estar em uma linha separada.\n\n"
                            f"{emoji.information} **Formato esperado:**\n"
                            f"```\n"
                            f"item1\n"
                            f"item2\n"
                            f"item3\n"
                            f"```\n\n"
                            f"{emoji.warn} **Atenção:** Você tem 5 minutos para enviar o arquivo."
                        ),
                        **embed_kwargs
                    )
                    await dm_channel.send(embed=embed)
                else:
                    container_kwargs = {}
                    if primary_color_hex:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.folder}\n-# **Upload de Estoque**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"-# Produto: **{product_name}**\n"
                            f"-# Campo: **{campo_name}**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"Por favor, envie um arquivo **.txt** com os itens de estoque.\n"
                            f"Cada item deve estar em uma linha separada."
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"{emoji.information} **Formato esperado:**\n"
                            f"```\n"
                            f"item1\n"
                            f"item2\n"
                            f"item3\n"
                            f"```"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"{emoji.warn} **Atenção:** Você tem 5 minutos para enviar o arquivo."
                        ),
                        **container_kwargs
                    )
                    await dm_channel.send(
                        components=[container],
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                
                await inter.response.send_message(
                    f"{emoji.correct} Verifique sua DM! Enviei instruções para o upload do arquivo.",
                    ephemeral=True
                )
            except disnake.Forbidden:
                await inter.response.send_message(
                    f"{emoji.wrong} Não foi possível enviar uma DM. Por favor, habilite 'Mensagens diretas' nas configurações de privacidade do servidor.",
                    ephemeral=True
                )
                # Remover do tracking se não conseguiu enviar DM
                self.pending_uploads.pop(inter.user.id, None)
            except Exception as e:
                await inter.response.send_message(
                    f"{emoji.wrong} Ocorreu um erro ao tentar enviar a DM: {str(e)}",
                    ephemeral=True
                )
                self.pending_uploads.pop(inter.user.id, None)
            return

    @commands.Cog.listener("on_message")
    async def on_dm_message(self, message: disnake.Message):
        """Processa arquivos .txt enviados em DM para upload de estoque"""
        # Ignorar mensagens de bots
        if message.author.bot:
            return
        
        # Verificar se é uma DM
        if not isinstance(message.channel, disnake.DMChannel):
            return
        
        user_id = message.author.id
        
        # Verificar se há upload pendente para este usuário
        if user_id not in self.pending_uploads:
            return
        
        upload_info = self.pending_uploads[user_id]
        
        # Verificar timeout (5 minutos)
        import time
        if time.time() - upload_info["timestamp"] > 300:  # 5 minutos
            self.pending_uploads.pop(user_id, None)
            from functions.emoji import emoji
            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=f"{emoji.wrong} O tempo para enviar o arquivo expirou. Por favor, inicie o processo novamente.",
                    **embed_kwargs
                )
                await message.channel.send(embed=embed)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} O tempo para enviar o arquivo expirou. Por favor, inicie o processo novamente."),
                    **container_kwargs
                )
                await message.channel.send(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            return
        
        # Verificar se há anexos
        if not message.attachments:
            from functions.emoji import emoji
            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=f"{emoji.warn} Por favor, envie um arquivo **.txt** como anexo.",
                    **embed_kwargs
                )
                await message.channel.send(embed=embed)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.warn} Por favor, envie um arquivo **.txt** como anexo."),
                    **container_kwargs
                )
                await message.channel.send(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            return
        
        # Procurar arquivo .txt
        txt_attachment = None
        for attachment in message.attachments:
            if attachment.filename.lower().endswith('.txt'):
                txt_attachment = attachment
                break
        
        if not txt_attachment:
            from functions.emoji import emoji
            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=f"{emoji.wrong} O arquivo deve ser um **.txt**. Por favor, envie um arquivo com extensão .txt",
                    **embed_kwargs
                )
                await message.channel.send(embed=embed)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} O arquivo deve ser um **.txt**. Por favor, envie um arquivo com extensão .txt"),
                    **container_kwargs
                )
                await message.channel.send(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            return
        
        # Processar arquivo .txt
        try:
            # Ler conteúdo do arquivo
            file_content = await txt_attachment.read()
            content_text = file_content.decode('utf-8')
            
            # Processar linhas
            lines = content_text.split('\n')
            items = [line.strip() for line in lines if line.strip()]
            
            # Limitar cada item a 2000 caracteres
            MAX_ITEM_LENGTH = 2000
            items = [item[:MAX_ITEM_LENGTH] if len(item) > MAX_ITEM_LENGTH else item for item in items]
            
            # Validar quantidade de itens
            MAX_ITEMS_PER_ADD = 10000  # Limite mais alto para upload de arquivo
            if not items:
                from functions.emoji import emoji
                mode = db.get_document("custom_mode").get("mode")
                color_data = db.get_document("custom_colors")
                primary_color_hex = color_data.get("primary")
                
                if mode == "embed":
                    embed_kwargs = {}
                    if primary_color_hex:
                        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                    embed = disnake.Embed(
                        description=f"{emoji.wrong} Nenhum item válido encontrado no arquivo.",
                        **embed_kwargs
                    )
                    await message.channel.send(embed=embed)
                else:
                    container_kwargs = {}
                    if primary_color_hex:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.wrong} Nenhum item válido encontrado no arquivo."),
                        **container_kwargs
                    )
                    await message.channel.send(
                        components=[container],
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                return
            
            if len(items) > MAX_ITEMS_PER_ADD:
                from functions.emoji import emoji
                mode = db.get_document("custom_mode").get("mode")
                color_data = db.get_document("custom_colors")
                primary_color_hex = color_data.get("primary")
                
                if mode == "embed":
                    embed_kwargs = {}
                    if primary_color_hex:
                        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                    embed = disnake.Embed(
                        description=f"{emoji.wrong} Máximo de {MAX_ITEMS_PER_ADD} itens por arquivo. Você tentou adicionar {len(items)} itens.",
                        **embed_kwargs
                    )
                    await message.channel.send(embed=embed)
                else:
                    container_kwargs = {}
                    if primary_color_hex:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(f"{emoji.wrong} Máximo de {MAX_ITEMS_PER_ADD} itens por arquivo. Você tentou adicionar {len(items)} itens."),
                        **container_kwargs
                    )
                    await message.channel.send(
                        components=[container],
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                return
            
            product_id = upload_info["product_id"]
            field_id = upload_info["field_id"]
            
            # Adicionar itens ao estoque centralizado
            should_notify = StockManager.add_stock_items(product_id, field_id, items)
            
            # Se precisa notificar, chamar função assíncrona
            if should_notify:
                # Obter bot do cog
                bot = self.bot
                if bot:
                    # Criar tarefa assíncrona para notificar
                    import asyncio
                    asyncio.create_task(
                        StockManager._notify_stock_available(product_id, field_id, bot)
                    )
            
            # Atualizar timestamp no products
            from functions.loja_products import get_products, save_products
            products = get_products()
            product = (products or {}).get(product_id) or {}
            campos = product.get("campos") or {}
            field = campos.get(field_id) or {}
            
            # Desativar estoque infinito ao adicionar estoque normal via upload
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
            campos[field_id] = field
            product["campos"] = campos
            info = product.get("info") or {}
            info["updated_at"] = int(disnake.utils.utcnow().timestamp())
            product["info"] = info
            products[product_id] = product
            save_products(products)
            
            # Sincronizar silenciosamente todas as mensagens do produto
            from modules.loja.products.product.edit import sync_product_messages_silently
            await sync_product_messages_silently(self.bot, product_id)
            
            # Remover do tracking
            self.pending_uploads.pop(user_id, None)
            
            # Enviar confirmação
            from functions.emoji import emoji
            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=(
                        f"{emoji.correct} **Upload concluído com sucesso!**\n\n"
                        f"-# Itens adicionados: `{len(items)}`\n"
                        f"-# Produto: **{product.get('name', product_id)}**\n"
                        f"-# Campo: **{field.get('name', field_id)}**"
                    ),
                    **embed_kwargs
                )
                await message.channel.send(embed=embed)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.correct}\n-# **Upload concluído com sucesso!**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"-# Itens adicionados: `{len(items)}`\n"
                        f"-# Produto: **{product.get('name', product_id)}**\n"
                        f"-# Campo: **{field.get('name', field_id)}**"
                    ),
                    **container_kwargs
                )
                await message.channel.send(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
        
        except UnicodeDecodeError:
            from functions.emoji import emoji
            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=f"{emoji.wrong} Erro ao ler o arquivo. Certifique-se de que o arquivo está codificado em UTF-8.",
                    **embed_kwargs
                )
                await message.channel.send(embed=embed)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Erro ao ler o arquivo. Certifique-se de que o arquivo está codificado em UTF-8."),
                    **container_kwargs
                )
                await message.channel.send(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
        except Exception as e:
            from functions.emoji import emoji
            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors")
            primary_color_hex = color_data.get("primary")
            
            if mode == "embed":
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(
                    description=f"{emoji.wrong} Erro ao processar o arquivo: {str(e)}",
                    **embed_kwargs
                )
                await message.channel.send(embed=embed)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"{emoji.wrong} Erro ao processar o arquivo: {str(e)}"),
                    **container_kwargs
                )
                await message.channel.send(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )


def setup(bot: commands.Bot):
    bot.add_cog(EstoqueCampoCog(bot))
