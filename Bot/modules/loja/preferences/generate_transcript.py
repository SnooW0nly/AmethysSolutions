"""
Geração de transcripts para carrinhos de compras
"""
import disnake
import chat_exporter as dht
import io
from disnake.ext import commands
from datetime import datetime
from typing import Optional
from functions.database import database as db
from functions.emoji import emoji


async def generate_cart_transcript(
    thread: disnake.Thread,
    bot: commands.Bot,
    cart: dict,
    limit: Optional[int] = None
) -> Optional[disnake.File]:
    """
    Gera um arquivo de transcript em HTML para um carrinho/thread específico.
    
    :param thread: A thread do carrinho.
    :param bot: A instância do bot para buscar membros fora da guilda.
    :param cart: Dados do carrinho para incluir informações adicionais.
    :param limit: O número máximo de mensagens a serem incluídas.
    :return: Um objeto disnake.File contendo o transcript, ou None se falhar.
    """
    try:
        transcript_html = await dht.export(
            thread,
            limit=limit,
            bot=bot,
        )

        if not transcript_html:
            return None
        
        # Adicionar informações do carrinho ao início do HTML
        cart_info_html = _build_cart_info_html(cart)
        if cart_info_html:
            # Inserir antes do fechamento do body ou no início
            transcript_html = transcript_html.replace(
                '</body>',
                f'{cart_info_html}</body>'
            )

        return disnake.File(
            io.BytesIO(transcript_html.encode('utf-8')),
            filename=f"transcript-carrinho-{thread.id}.html",
        )
    except Exception as e:
        print(f"Falha ao gerar transcript do carrinho: {e}")
        import traceback
        traceback.print_exc()
        return None


def _build_cart_info_html(cart: dict) -> str:
    """Constrói HTML com informações do carrinho"""
    try:
        products = db.get_document("loja_products") or {}
        items = cart.get("items", [])
        
        if not items:
            return ""
        
        # Informações básicas
        user_id = cart.get("user_id", "Desconhecido")
        status = cart.get("status", "unknown")
        created_at = cart.get("created_at", 0)
        total_price = cart.get("total_price", 0)
        discount_amount = cart.get("discount_amount", 0) or 0
        final_price = max(0, total_price - discount_amount)
        payment_method = cart.get("payment_method", "unknown")
        coupon_code = cart.get("coupon_code")
        
        # Formatar data
        if created_at:
            dt = datetime.fromtimestamp(created_at)
            date_str = dt.strftime("%d/%m/%Y %H:%M:%S")
        else:
            date_str = "Data não disponível"
        
        # Status traduzido
        status_map = {
            "cart": "Carrinho",
            "pending": "Pagamento Pendente",
            "approved": "Aprovado",
            "cancelled": "Cancelado",
            "expired": "Expirado"
        }
        status_text = status_map.get(status, status)
        
        # Método de pagamento traduzido
        payment_map = {
            "pix": "PIX",
            "card": "Cartão de Crédito",
            "crypto": "Criptomoeda"
        }
        payment_text = payment_map.get(payment_method, payment_method.upper())
        
        # Listar produtos
        products_html = ""
        for item in items:
            product_id = item.get("product_id")
            campo_id = item.get("campo_id")
            quantity = item.get("quantity", 1)
            price_per_unit = item.get("price_per_unit", 0)
            item_total = item.get("item_total", 0)
            
            product = products.get(product_id, {})
            product_name = product.get("name", "Produto não encontrado")
            campos = product.get("campos", {})
            campo = campos.get(campo_id, {})
            campo_name = campo.get("name", "Campo não encontrado")
            
            # Formatar preços
            price_per_unit_str = f"{price_per_unit:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            item_total_str = f"{item_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            products_html += f"""
            <div style="margin: 10px 0; padding: 10px; background: #2f3136; border-radius: 5px;">
                <strong>{product_name}</strong> - {campo_name}<br>
                Quantidade: {quantity} | Preço unitário: R$ {price_per_unit_str} | Total: R$ {item_total_str}
            </div>
            """
        
        # Formatar valores monetários
        total_price_str = f"{total_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        discount_amount_str = f"{discount_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if discount_amount > 0 else "0,00"
        final_price_str = f"{final_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # HTML para desconto e cupom
        discount_html = f'<strong>Desconto:</strong> R$ {discount_amount_str}<br>' if discount_amount > 0 else ''
        coupon_html = f'<strong>Cupom:</strong> {coupon_code}<br>' if coupon_code else ''
        
        # HTML completo
        html = f"""
        <div style="margin: 20px 0; padding: 20px; background: #23272a; border-radius: 10px; border-left: 4px solid #5865f2;">
            <h2 style="color: #5865f2; margin-top: 0;">📋 Informações do Carrinho</h2>
            
            <div style="margin: 10px 0;">
                <strong>ID do Usuário:</strong> {user_id}<br>
                <strong>Status:</strong> {status_text}<br>
                <strong>Data de Criação:</strong> {date_str}<br>
                <strong>Método de Pagamento:</strong> {payment_text}<br>
            </div>
            
            <h3 style="color: #5865f2; margin-top: 20px;">🛒 Produtos</h3>
            {products_html}
            
            <div style="margin: 15px 0; padding: 15px; background: #2f3136; border-radius: 5px;">
                <strong>Subtotal:</strong> R$ {total_price_str}<br>
                {discount_html}
                {coupon_html}
                <strong style="font-size: 1.2em; color: #57f287;">Total Final: R$ {final_price_str}</strong>
            </div>
        </div>
        """
        
        return html
    except Exception as e:
        print(f"Erro ao construir HTML de informações do carrinho: {e}")
        return ""


async def send_cart_transcript_to_channel(
    bot: commands.Bot,
    transcript_file: disnake.File,
    channel_id: int,
    cart: dict
) -> bool:
    """
    Envia o transcript do carrinho para um canal de log.
    
    :param bot: A instância do bot.
    :param transcript_file: O arquivo de transcript a ser enviado.
    :param channel_id: O ID do canal de log.
    :param cart: Dados do carrinho para informações adicionais.
    :return: True se enviado com sucesso, False caso contrário.
    """
    try:
        log_channel = bot.get_channel(channel_id)
        if not log_channel:
            return False
        
        # Obter informações do usuário
        user_id = cart.get("user_id")
        user = None
        if user_id:
            try:
                user = await bot.fetch_user(user_id)
            except:
                pass
        
        # Criar embed com informações resumidas
        mode = db.get_document("custom_mode").get("mode", "embed")
        products = db.get_document("loja_products") or {}
        items = cart.get("items", [])
        
        total_price = cart.get("total_price", 0)
        discount_amount = cart.get("discount_amount", 0) or 0
        final_price = max(0, total_price - discount_amount)
        
        # Formatar preço final
        final_price_str = f"{final_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Listar produtos resumidos
        products_list = []
        for item in items[:5]:  # Limitar a 5 produtos no resumo
            product_id = item.get("product_id")
            campo_id = item.get("campo_id")
            quantity = item.get("quantity", 1)
            
            product = products.get(product_id, {})
            product_name = product.get("name", "Produto")
            campos = product.get("campos", {})
            campo = campos.get(campo_id, {})
            campo_name = campo.get("name", "Campo")
            
            products_list.append(f"{product_name} - {campo_name} (x{quantity})")
        
        if len(items) > 5:
            products_list.append(f"... e mais {len(items) - 5} produto(s)")
        
        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.double_speech} Transcript de Carrinho",
                description=f"**Usuário:** {user.mention if user else f'ID: {user_id}'}\n**Total:** R$ {final_price_str}",
                color=disnake.Color.blue(),
                timestamp=datetime.utcnow()
            )
            if products_list:
                embed.add_field(
                    name="Produtos",
                    value="\n".join(products_list),
                    inline=False
                )
            
            await log_channel.send(embed=embed, file=transcript_file)
        else:
            # Modo Container
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            await log_channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.double_speech}\n-# **Transcript de Carrinho**"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"-# **Usuário:** {user.mention if user else f'ID: {user_id}'}\n"
                            f"-# **Total:** R$ {final_price_str}"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"-# **Produtos:**\n" + "\n".join(products_list)) if products_list else disnake.ui.TextDisplay("-# Sem produtos"),
                        **container_kwargs
                    )
                ],
                file=transcript_file,
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        
        return True
    except Exception as e:
        print(f"Erro ao enviar transcript para canal: {e}")
        import traceback
        traceback.print_exc()
        return False

