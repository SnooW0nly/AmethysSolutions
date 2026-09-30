"""
Sistema de logs de pedidos e eventos de compra
"""
import disnake
from disnake.ext import commands
from datetime import datetime
import io
from typing import Optional, List, Dict, Any
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils
from functions.receipt_generator import ReceiptGenerator
import os
import aiohttp


class PurchaseLogsSystem(commands.Cog):
    """Sistema de logs de pedidos e eventos de compra"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.receipt_gen = ReceiptGenerator()
    
    @staticmethod
    def _get_mode_and_color() -> tuple:
        """Retorna o modo de exibição e cor padrão"""
        mode = db.get_document("custom_mode").get("mode", "embed")
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        color = None
        if primary_color_hex:
            try:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
                color = disnake.Colour(primary_color)
            except:
                pass
        
        return mode, color

    @staticmethod
    def _get_receipt_config() -> dict:
        """Retorna a configuração de personalização dos logs de vendas (evento público)"""
        return db.get_document("loja_receipt_customization")
    
    @staticmethod
    def _create_stock_file(items: List[str]) -> disnake.File:
        """Cria um arquivo .txt com os itens do estoque"""
        content = "=== ITENS RECEBIDOS ===\n\n"
        for i, item in enumerate(items, 1):
            content += f"{i}. {item}\n"
        
        content += f"\n=== TOTAL: {len(items)} item(s) ===\n"
        content += f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
        
        file_buffer = io.BytesIO(content.encode('utf-8'))
        file_buffer.seek(0)
        return disnake.File(file_buffer, filename="estoque_recebido.txt")
    
    async def send_order_log(
        self,
        guild: disnake.Guild,
        user: disnake.User,
        product_name: str,
        campo_name: str,
        quantity: int,
        price: float,
        payment_method: str,
        items: Optional[List[str]] = None,
        delivery_type: str = "automatic",
        cart_id: Optional[str] = None,
        source: str = "discord"
    ):
        """Envia log detalhado do pedido para o canal de logs de pedidos"""
        try:
            # Obter canal de logs
            canais = db.get_document("canais") or {}
            log_channel_id = canais.get("canal_de_logs_de_pedidos")
            
            if not log_channel_id:
                print(f"[LOG PEDIDOS] Canal de logs de pedidos não configurado")
                return
            
            try:
                channel = guild.get_channel(int(log_channel_id))
            except (ValueError, TypeError) as e:
                print(f"[LOG PEDIDOS] Erro ao converter channel_id: {log_channel_id} - {e}")
                return
            
            if not channel:
                print(f"[LOG PEDIDOS] Canal {log_channel_id} não encontrado no servidor")
                return
            
            mode, color = self._get_mode_and_color()
            
            # Formatar método de pagamento
            payment_methods_map = {
                "pix": "PIX",
                "card": "Cartão de Crédito",
                "crypto": "Criptomoeda"
            }
            payment_display = payment_methods_map.get(payment_method, payment_method.upper())
            
            # Formatar preço
            price_display = utils.format_price_brl(price)
            
            # Preparar arquivo de estoque se necessário
            stock_file = None
            stock_text = None
            
            # Validar se items é uma lista
            if items and isinstance(items, list) and len(items) > 0:
                items_text = "\n".join([f"`{i+1}.` {item}" for i, item in enumerate(items)])
                if len(items_text) > 2000:
                    stock_file = self._create_stock_file(items)
                    stock_text = f"*Arquivo anexado com {len(items)} item(s)*"
                else:
                    stock_text = items_text
            
            if mode == "embed":
                # Criar embed
                embed = disnake.Embed(
                    title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Novo Pedido Realizado",
                    description=(
                        f"**Cliente:** {user.mention} (`{user.id}`)\n"
                        f"**Produto:** {product_name}\n"
                        f"**Campo:** {campo_name}\n"
                        f"**Quantidade:** {quantity}\n"
                        f"**Valor:** {price_display}\n"
                        f"**Método:** {payment_display}\n"
                        f"**Origem:** {'📱 Telegram' if source == 'telegram' else '🎮 Discord'}\n"
                        f"**Tipo de Entrega:** {'Manual' if delivery_type == 'manual' else 'Automática'}\n"
                        f"**ID do Pedido:** `{cart_id or 'N/A'}`"
                    ),
                    color=color or disnake.Color.green(),
                    timestamp=datetime.now()
                )
                
                embed.set_footer(
                    text=f"Pedido processado • {guild.name}",
                    icon_url=guild.icon.url if guild.icon else None
                )
                
                # Enviar mensagem do log primeiro
                log_message = await channel.send(embed=embed)
                
                # Se houver estoque entregue, sempre enviar arquivo .txt como resposta ao log
                if items and log_message:
                    try:
                        stock_file_reply = self._create_stock_file(items)
                        await log_message.reply(f"{emoji.cardbox} **Estoque Entregue:**", file=stock_file_reply)
                    except Exception as e:
                        print(f"[LOG PEDIDOS] Erro ao enviar resposta com estoque: {e}")
                
                print(f"[LOG PEDIDOS] Log enviado com sucesso para {channel.name} (embed)")
            
            else:
                # Criar container
                container_kwargs = {}
                if color:
                    container_kwargs["accent_colour"] = color
                
                # Construir lista de componentes do container (sem None)
                container_children = [
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Novo Pedido Realizado"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(f"## {emoji.member} Cliente\n-# {user.mention} (`{user.id}`)"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"## {emoji.bag} Produto\n"
                        f"-# **Nome:** {product_name}\n"
                        f"-# **Campo:** {campo_name}\n"
                        f"-# **Quantidade:** `{quantity}`"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"## {emoji.dollar} Pagamento\n"
                        f"-# **Valor:** `{price_display}`\n"
                        f"-# **Método:** {payment_display}\n"
                        f"-# **Origem:** {'📱 Telegram' if source == 'telegram' else '🎮 Discord'}"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        f"## {emoji.truck if delivery_type == 'manual' else emoji.correct} Entrega\n"
                        f"-# **Tipo:** {'Manual' if delivery_type == 'manual' else 'Automática'}\n"
                        f"-# **ID do Pedido:** `{cart_id or 'N/A'}`"
                    )
                ]
                
                components = [
                    disnake.ui.Container(
                        *container_children,
                        **container_kwargs
                    )
                ]
                
                # Enviar mensagem do log primeiro
                log_message = await channel.send(
                    components=components,
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
                
                # Se houver estoque entregue, sempre enviar arquivo .txt como resposta ao log
                if items and log_message:
                    try:
                        stock_file_reply = self._create_stock_file(items)
                        await log_message.reply(f"{emoji.cardbox} **Estoque Entregue:**", file=stock_file_reply)
                    except Exception as e:
                        print(f"[LOG PEDIDOS] Erro ao enviar resposta com estoque: {e}")
                
                print(f"[LOG PEDIDOS] Log enviado com sucesso para {channel.name} (container)")
        
        except Exception as e:
            print(f"[LOG EVENTO] ERRO GERAL ao enviar evento de compra: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_cart_created_log(
        self,
        guild: disnake.Guild,
        user: disnake.User,
        product_name: str,
        campo_name: str,
        quantity: int,
        price: float,
        payment_method: str,
        cart_url: str,
        cart_id: str
    ):
        """Envia log de criação de carrinho"""
        try:
            # Obter canal de logs
            canais = db.get_document("canais") or {}
            log_channel_id = canais.get("canal_de_logs_de_pedidos")
            
            if not log_channel_id:
                print(f"[LOG CARRINHO] Canal de logs de pedidos não configurado")
                return
            
            try:
                channel = guild.get_channel(int(log_channel_id))
            except (ValueError, TypeError) as e:
                print(f"[LOG CARRINHO] Erro ao converter channel_id: {log_channel_id} - {e}")
                return
            
            if not channel:
                print(f"[LOG CARRINHO] Canal {log_channel_id} não encontrado no servidor")
                return
            
            mode, color = self._get_mode_and_color()
            
            # Formatar método de pagamento
            payment_methods_map = {
                "pix": "PIX",
                "pix_manual": "PIX Manual",
                "card": "Cartão de Crédito",
                "crypto": "Criptomoeda",
                "mercado_pago": "Mercado Pago",
                "stripe": "Stripe",
                "paypal": "PayPal"
            }
            payment_display = payment_methods_map.get(payment_method, payment_method.upper())
            
            # Formatar preço
            price_display = utils.format_price_brl(price)
            
            if mode == "embed":
                embed = disnake.Embed(
                    title=f"Carrinho Criado",
                    description=(
                        f"**Cliente:** {user.mention} (`{user.id}`)\n"
                        f"**Produto:** {product_name}\n"
                        f"**Campo:** {campo_name}\n"
                        f"**Quantidade:** {quantity}\n"
                        f"**Valor:** {price_display}\n"
                        f"**Método:** {payment_display}\n"
                        f"**Status:** Aguardando Pagamento"
                    ),
                    color=disnake.Color.blue(),
                    timestamp=datetime.now()
                )
                
                embed.set_footer(
                    text=f"ID: {cart_id} • {guild.name}",
                    icon_url=guild.icon.url if guild.icon else None
                )
                
                components = [
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Abrir Carrinho",
                            style=disnake.ButtonStyle.link,
                            url=cart_url,
                            emoji=emoji.cart
                        )
                    )
                ]
                
                await channel.send(embed=embed, components=components)
                print(f"[LOG CARRINHO] Log de carrinho criado enviado para {channel.name} (embed)")
            
            else:
                container_kwargs = {}
                if color:
                    container_kwargs["accent_colour"] = color
                
                components = [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Carrinho Criado"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"**Cliente:** {user.mention}\n"
                            f"**Produto:** {product_name}\n"
                            f"**Campo:** {campo_name}\n"
                            f"**Quantidade:** `{quantity}`\n"
                            f"**Valor:** `{price_display}`\n"
                            f"**Método:** {payment_display}\n"
                            f"**Status:** Aguardando Pagamento"
                        ),
                        **container_kwargs
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Abrir Carrinho",
                            style=disnake.ButtonStyle.link,
                            url=cart_url,
                            emoji=emoji.cart
                        )
                    )
                ]
                
                await channel.send(
                    components=components,
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
                print(f"[LOG CARRINHO] Log de carrinho criado enviado para {channel.name} (container)")
        
        except Exception as e:
            print(f"[LOG CARRINHO] Erro ao enviar log de carrinho criado: {e}")
            import traceback
            traceback.print_exc()
    
    async def send_purchase_event(
        self,
        guild: disnake.Guild,
        user: disnake.User,
        product_name: str,
        campo_name: str,
        quantity: int,
        price: float,
        product_id: str,
        original_price: float = None,
        discount_amount: float = None,
        coupon_code: str = None
    ):
        """Envia evento público de compra (imagem, embed ou componentes)"""
        print(f"[LOG EVENTO] ✅ Iniciando send_purchase_event para {user.name}")
        avatar_path = f"temp_avatar_{user.id}.png"
        icon_path   = f"temp_icon_{guild.id}.png"
        try:
            # Checar se o evento público está habilitado
            receipt_cfg = self._get_receipt_config()
            if not receipt_cfg.get("enabled", True) is False:
                pass  # enabled por padrão; só bloqueia se explicitamente False
            if receipt_cfg.get("enabled") is False:
                print(f"[LOG EVENTO] Evento público desabilitado nas configurações")
                return

            # Obter canal de eventos
            canais = db.get_document("canais") or {}
            event_channel_id = canais.get("canal_de_evento_de_compras")
            print(f"[LOG EVENTO] event_channel_id: {event_channel_id}")
            
            if not event_channel_id:
                print(f"[LOG EVENTO] Canal de evento de compras não configurado")
                return
            
            try:
                channel = guild.get_channel(int(event_channel_id))
                print(f"[LOG EVENTO] Canal encontrado: {channel}")
            except (ValueError, TypeError) as e:
                print(f"[LOG EVENTO] Erro ao converter channel_id: {event_channel_id} - {e}")
                return
            
            if not channel:
                print(f"[LOG EVENTO] Canal {event_channel_id} não encontrado no servidor")
                return

            # Obter link do produto
            products = db.get_document("loja_products") or {}
            product = products.get(product_id, {})
            product_url = None
            product_messages = product.get("messages", [])
            if product_messages:
                latest_message = max(product_messages, key=lambda m: m.get("created_at", 0))
                product_channel_id = latest_message.get("channel_id")
                product_message_id = latest_message.get("message_id")
                if product_channel_id and product_message_id:
                    product_url = f"https://discord.com/channels/{guild.id}/{product_channel_id}/{product_message_id}"

            buy_button_row = []
            if product_url:
                buy_button_row = [disnake.ui.ActionRow(
                    disnake.ui.Button(label="Comprar Também", style=disnake.ButtonStyle.link, url=product_url)
                )]

            receipt_mode = receipt_cfg.get("mode", "image")
            footer_text  = receipt_cfg.get("footer_text", "amethys.solutions")
            price_display = utils.format_price_brl(price)

            # ── MODO EMBED ──────────────────────────────────────────────────
            if receipt_mode == "embed":
                _, color = self._get_mode_and_color()
                embed = disnake.Embed(
                    title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Compra Realizada",
                    description=(
                        f"**Cliente:** {user.mention}\n"
                        f"**Produto:** {product_name}\n"
                        f"**Campo:** {campo_name}\n"
                        f"**Quantidade:** {quantity}\n"
                        f"**Valor:** {price_display}"
                        + (f"\n**Desconto:** -{utils.format_price_brl(discount_amount)}" if discount_amount else "")
                        + (f"\n**Cupom:** `{coupon_code}`" if coupon_code else "")
                    ),
                    color=color or disnake.Color.green(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"{footer_text} • {guild.name}", icon_url=guild.icon.url if guild.icon else None)
                embed.set_thumbnail(url=user.display_avatar.url)
                await channel.send(embed=embed, components=buy_button_row if buy_button_row else None)
                print(f"[LOG EVENTO] Evento enviado como embed para {channel.name}")
                return

            # ── MODO COMPONENTES ─────────────────────────────────────────────
            if receipt_mode == "components":
                _, color = self._get_mode_and_color()
                container_kwargs = {}
                if color:
                    container_kwargs["accent_colour"] = color
                desc = (
                    f"**Produto:** {product_name}  |  {campo_name}\n"
                    f"**Quantidade:** `{quantity}`\n"
                    f"**Valor:** `{price_display}`"
                    + (f"\n**Desconto:** `-{utils.format_price_brl(discount_amount)}`" if discount_amount else "")
                    + (f"\n**Cupom:** `{coupon_code}`" if coupon_code else "")
                )
                components = [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Compra Realizada"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"## {emoji.member} {user.mention}"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(desc),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"-# {footer_text}"),
                        **container_kwargs
                    ),
                    *buy_button_row
                ]
                await channel.send(components=components, flags=disnake.MessageFlags(is_components_v2=True))
                print(f"[LOG EVENTO] Evento enviado como componentes para {channel.name}")
                return

            # ── MODO BUILDER ─────────────────────────────────────────────────
            if receipt_mode == "builder":
                editor_data = receipt_cfg.get("builder_editor", {})
                if editor_data:
                    from commands.admin.anunciar.builder import Builder as _Builder
                    variables = {
                        "cliente":    f"{user.display_name} (@{user.name})",
                        "produto":    f"{product_name} | {campo_name}",
                        "valor":      price_display,
                        "quantidade": str(quantity),
                        "desconto":   utils.format_price_brl(discount_amount) if discount_amount else "—",
                        "cupom":      coupon_code or "—",
                    }
                    def _apply(text: str) -> str:
                        if not text: return text
                        for k, v in variables.items():
                            text = text.replace(f"{{{k}}}", v)
                        return text
                    editor = editor_data.copy()
                    if editor.get("content"):
                        editor["content"] = _apply(editor["content"])
                    if editor.get("embed", {}).get("description"):
                        editor["embed"] = dict(editor["embed"])
                        editor["embed"]["description"] = _apply(editor["embed"]["description"])
                    if editor.get("container"):
                        editor["container"] = _apply(editor["container"])
                    if "botoes" in editor:
                        editor["buttons"] = editor.pop("botoes")
                    cfg = {"message": editor}
                    built = await _Builder.build_from_cfg(cfg)
                    if built["mode"] == "v2":
                        await channel.send(
                            components=built["components"] + buy_button_row,
                            flags=built["flags"],
                            allowed_mentions=disnake.AllowedMentions.none(),
                        )
                    else:
                        kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
                        if built.get("content"):    kwargs["content"]    = built["content"]
                        if built.get("embed"):      kwargs["embed"]      = built["embed"]
                        if built.get("files"):      kwargs["files"]      = built["files"]
                        kwargs["components"] = (built.get("components") or []) + buy_button_row or None
                        await channel.send(**kwargs)
                    print(f"[LOG EVENTO] Evento enviado como builder para {channel.name}")
                    return

            # ── MODO IMAGEM (PILLOW) — padrão ────────────────────────────────
            print(f"[LOG EVENTO] Prosseguindo com download de avatar e ícone")
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(str(user.display_avatar.url)) as resp:
                        if resp.status == 200:
                            with open(avatar_path, "wb") as f:
                                f.write(await resp.read())
                except Exception as e:
                    print(f"[LOG EVENTO] Erro ao baixar avatar: {e}")
                    avatar_path = None
                
                try:
                    if guild.icon:
                        async with session.get(str(guild.icon.url)) as resp:
                            if resp.status == 200:
                                with open(icon_path, "wb") as f:
                                    f.write(await resp.read())
                    else:
                        icon_path = None
                except Exception as e:
                    print(f"[LOG EVENTO] Erro ao baixar ícone do servidor: {e}")
                    icon_path = None

            print(f"[LOG EVENTO] Gerando recibo com desconto: {discount_amount}, cupom: {coupon_code}")
            receipt_buffer = self.receipt_gen.generate_receipt(
                user_name=user.display_name,
                user_handle=user.name,
                user_avatar_path=avatar_path,
                product_name=f"{product_name} | {campo_name}",
                quantity=quantity,
                price=price,
                guild_name=guild.name,
                guild_icon_path=icon_path,
                footer_text=footer_text,
                original_price=original_price,
                discount_amount=discount_amount,
                coupon_code=coupon_code,
                custom_bg_color=receipt_cfg.get("bg_color"),
                custom_card_color=receipt_cfg.get("card_color"),
                custom_accent_color=receipt_cfg.get("accent_color"),
            )
            
            file = disnake.File(receipt_buffer, filename="receita.png")
            print(f"[LOG EVENTO] Arquivo de recibo criado com sucesso")

            await channel.send(file=file, components=buy_button_row if buy_button_row else None)
            print(f"[LOG EVENTO] Evento de compra enviado como imagem para {channel.name}")
        
        except Exception as e:
            print(f"[LOG EVENTO] ERRO ao enviar evento de compra: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            try:
                if avatar_path and os.path.exists(avatar_path):
                    os.remove(avatar_path)
                if icon_path and os.path.exists(icon_path):
                    os.remove(icon_path)
            except:
                pass


    async def send_purchase_event_bulk(
        self,
        guild: disnake.Guild,
        user: disnake.User,
        items: list,  # Lista de itens: [{product_name, campo_name, quantity, price, product_id}, ...]
        total_price: float,
        subtotal: float = None,
        discount_amount: float = None,
        coupon_code: str = None
    ):
        """Envia evento público de compra (imagem, embed ou componentes) com todos os itens"""
        print(f"[LOG EVENTO] ✅ Iniciando send_purchase_event_bulk para {user.name} com {len(items)} itens")
        avatar_path = f"temp_avatar_{user.id}.png"
        icon_path   = f"temp_icon_{guild.id}.png"
        try:
            # Checar se o evento público está habilitado
            receipt_cfg = self._get_receipt_config()
            if receipt_cfg.get("enabled") is False:
                print(f"[LOG EVENTO] Evento público desabilitado nas configurações")
                return

            # Obter canal de eventos
            canais = db.get_document("canais") or {}
            event_channel_id = canais.get("canal_de_evento_de_compras")
            print(f"[LOG EVENTO] event_channel_id: {event_channel_id}")
            
            if not event_channel_id:
                print(f"[LOG EVENTO] Canal de evento de compras não configurado")
                return
            
            try:
                channel = guild.get_channel(int(event_channel_id))
                print(f"[LOG EVENTO] Canal encontrado: {channel}")
            except (ValueError, TypeError) as e:
                print(f"[LOG EVENTO] Erro ao converter channel_id: {event_channel_id} - {e}")
                return
            
            if not channel:
                print(f"[LOG EVENTO] Canal {event_channel_id} não encontrado no servidor")
                return

            # Botão do primeiro produto
            buy_button_row = []
            if items:
                products = db.get_document("loja_products") or {}
                first_item = items[0]
                product = products.get(first_item.get("product_id"), {})
                product_url = None
                product_messages = product.get("messages", [])
                if product_messages:
                    latest_message = max(product_messages, key=lambda m: m.get("created_at", 0))
                    product_channel_id = latest_message.get("channel_id")
                    product_message_id = latest_message.get("message_id")
                    if product_channel_id and product_message_id:
                        product_url = f"https://discord.com/channels/{guild.id}/{product_channel_id}/{product_message_id}"
                if product_url:
                    buy_button_row = [disnake.ui.ActionRow(
                        disnake.ui.Button(label="Comprar Também", style=disnake.ButtonStyle.link, url=product_url)
                    )]
                    print(f"[LOG EVENTO] Botão de compra adicionado")

            receipt_mode  = receipt_cfg.get("mode", "image")
            footer_text   = receipt_cfg.get("footer_text", "amethys.solutions")
            total_display = utils.format_price_brl(total_price)

            # ── MODO EMBED ──────────────────────────────────────────────────
            if receipt_mode == "embed":
                _, color = self._get_mode_and_color()
                items_text = "\n".join(
                    f"`{i+1}.` {it.get('quantity')}x **{it.get('product_name')}** | {it.get('campo_name')} — {utils.format_price_brl(it.get('price', 0))}"
                    for i, it in enumerate(items)
                )
                embed = disnake.Embed(
                    title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Compra Realizada",
                    description=(
                        f"**Cliente:** {user.mention}\n\n"
                        f"{items_text}\n\n"
                        f"**Total:** {total_display}"
                        + (f"\n**Desconto:** -{utils.format_price_brl(discount_amount)}" if discount_amount else "")
                        + (f"\n**Cupom:** `{coupon_code}`" if coupon_code else "")
                    ),
                    color=color or disnake.Color.green(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"{footer_text} • {guild.name}", icon_url=guild.icon.url if guild.icon else None)
                embed.set_thumbnail(url=user.display_avatar.url)
                await channel.send(embed=embed, components=buy_button_row if buy_button_row else None)
                print(f"[LOG EVENTO] Evento bulk enviado como embed para {channel.name}")
                return

            # ── MODO COMPONENTES ─────────────────────────────────────────────
            if receipt_mode == "components":
                _, color = self._get_mode_and_color()
                container_kwargs = {}
                if color:
                    container_kwargs["accent_colour"] = color
                items_text = "\n".join(
                    f"-# `{i+1}.` {it.get('quantity')}x **{it.get('product_name')}** | {it.get('campo_name')} — `{utils.format_price_brl(it.get('price', 0))}`"
                    for i, it in enumerate(items)
                )
                total_line = f"**Total:** `{total_display}`"
                if discount_amount:
                    total_line += f"\n**Desconto:** `-{utils.format_price_brl(discount_amount)}`"
                if coupon_code:
                    total_line += f"\n**Cupom:** `{coupon_code}`"
                components = [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Compra Realizada"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"## {emoji.member} {user.mention}"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(items_text),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(total_line),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"-# {footer_text}"),
                        **container_kwargs
                    ),
                    *buy_button_row
                ]
                await channel.send(components=components, flags=disnake.MessageFlags(is_components_v2=True))
                print(f"[LOG EVENTO] Evento bulk enviado como componentes para {channel.name}")
                return

            # ── MODO BUILDER ─────────────────────────────────────────────────
            if receipt_mode == "builder":
                editor_data = receipt_cfg.get("builder_editor", {})
                if editor_data:
                    from commands.admin.anunciar.builder import Builder as _Builder
                    items_text = "\n".join(
                        f"{it.get('quantity')}x {it.get('product_name')} | {it.get('campo_name')} — {utils.format_price_brl(it.get('price', 0))}"
                        for it in items
                    )
                    variables = {
                        "cliente":    f"{user.display_name} (@{user.name})",
                        "produto":    items_text,
                        "valor":      total_display,
                        "quantidade": str(sum(it.get("quantity", 1) for it in items)),
                        "desconto":   utils.format_price_brl(discount_amount) if discount_amount else "—",
                        "cupom":      coupon_code or "—",
                    }
                    def _apply(text: str) -> str:
                        if not text: return text
                        for k, v in variables.items():
                            text = text.replace(f"{{{k}}}", v)
                        return text
                    editor = editor_data.copy()
                    if editor.get("content"):
                        editor["content"] = _apply(editor["content"])
                    if editor.get("embed", {}).get("description"):
                        editor["embed"] = dict(editor["embed"])
                        editor["embed"]["description"] = _apply(editor["embed"]["description"])
                    if editor.get("container"):
                        editor["container"] = _apply(editor["container"])
                    if "botoes" in editor:
                        editor["buttons"] = editor.pop("botoes")
                    cfg = {"message": editor}
                    built = await _Builder.build_from_cfg(cfg)
                    if built["mode"] == "v2":
                        await channel.send(
                            components=built["components"] + buy_button_row,
                            flags=built["flags"],
                            allowed_mentions=disnake.AllowedMentions.none(),
                        )
                    else:
                        kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
                        if built.get("content"):    kwargs["content"]    = built["content"]
                        if built.get("embed"):      kwargs["embed"]      = built["embed"]
                        if built.get("files"):      kwargs["files"]      = built["files"]
                        kwargs["components"] = (built.get("components") or []) + buy_button_row or None
                        await channel.send(**kwargs)
                    print(f"[LOG EVENTO] Evento bulk enviado como builder para {channel.name}")
                    return

            # ── MODO IMAGEM (PILLOW) — padrão ────────────────────────────────
            print(f"[LOG EVENTO] Prosseguindo com download de avatar e ícone")
            receipt_buffer = self.receipt_gen.generate_receipt(
                user_name=user.display_name,
                user_handle=user.name,
                user_avatar_path=avatar_path,
                items=items,
                total_price=total_price,
                guild_name=guild.name,
                guild_icon_path=icon_path,
                footer_text=footer_text,
                subtotal=subtotal,
                discount_amount=discount_amount,
                coupon_code=coupon_code,
                custom_bg_color=receipt_cfg.get("bg_color"),
                custom_card_color=receipt_cfg.get("card_color"),
                custom_accent_color=receipt_cfg.get("accent_color"),
            )
            
            file = disnake.File(receipt_buffer, filename="receita.png")
            print(f"[LOG EVENTO] Arquivo de recibo criado com sucesso")

            await channel.send(file=file, components=buy_button_row if buy_button_row else None)
            print(f"[LOG EVENTO] Evento de compra enviado como imagem para {channel.name}")
        
        except Exception as e:
            print(f"[LOG EVENTO] ERRO ao enviar evento de compra bulk: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            try:
                if avatar_path and os.path.exists(avatar_path):
                    os.remove(avatar_path)
                if icon_path and os.path.exists(icon_path):
                    os.remove(icon_path)
            except:
                pass


def setup(bot: commands.Bot):
    bot.add_cog(PurchaseLogsSystem(bot))
