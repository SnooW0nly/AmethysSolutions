"""
Sistema de entrega automática de produtos
"""
import disnake
import io
from datetime import datetime
from typing import List, Optional
from functions.emoji import emoji
from functions.database import database as db
from functions.utils import utils
from .stock_manager import StockManager


async def deliver_members_to_user(
    user: disnake.User,
    product_id: str,
    product_name: str,
    quantity: int,
    cart_id: str,
    thread: Optional[disnake.Thread] = None,
    guild: Optional[disnake.Guild] = None,
    valor_pago: float = 0.0,
) -> bool:
    """
    Entrega especial para produto de membros:
    envia DM com painel contendo botão de adicionar bot cloud e botão de puxar membros.
    """
    colors = db.get_document("custom_colors") or {}
    primary_hex = colors.get("primary", "#5c5ef0")
    try:
        accent = disnake.Colour(int(primary_hex.replace("#", ""), 16))
    except Exception:
        accent = disnake.Colour(0x5c5ef0)

    cloud_config = db.get_document("cloud_data") or {}
    auth_bot_id = cloud_config.get("client_id")
    invite_url = (
        f"https://discord.com/api/oauth2/authorize?client_id={auth_bot_id}"
        f"&permissions=8&scope=bot%20applications.commands"
        if auth_bot_id else None
    )

    mode = (db.get_document("custom_mode") or {}).get("mode", "components")

    body = (
        f"**Produto:** {product_name}\n"
        f"**Quantidade de membros:** `{quantity}`\n\n"
        f"**Como receber seus membros:**\n"
        f"1️⃣ Adicione o bot cloud ao seu servidor usando o botão abaixo.\n"
        f"2️⃣ Clique em **Puxar Membros** e informe o ID do servidor de destino."
    )

    row_btns = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Adicionar Bot Cloud",
            style=disnake.ButtonStyle.link,
            url=invite_url or "https://discord.com",
            emoji="🤖",
            disabled=not invite_url,
        ),
        disnake.ui.Button(
            label="Puxar Membros",
            style=disnake.ButtonStyle.green,
            custom_id=f"members_delivery_pull:{product_id}:{quantity}:{cart_id}",
            emoji="🧑‍🤝‍🧑",
        ),
    )

    dm_sent = False
    try:
        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.correct} Membros Prontos para Entrega!",
                description=body,
                color=accent,
            )
            await user.send(embed=embed, components=[row_btns])
        else:
            await user.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.correct} Membros Prontos para Entrega!"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(body),
                        disnake.ui.Separator(),
                        row_btns,
                        accent_colour=accent,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        dm_sent = True
    except disnake.Forbidden:
        dm_sent = False

    # Se não conseguiu enviar DM, postar no thread do carrinho
    if not dm_sent and thread:
        fallback_body = f"{user.mention}\n\n{body}"
        try:
            if mode == "embed":
                embed = disnake.Embed(
                    title=f"{emoji.correct} Membros Prontos para Entrega!",
                    description=fallback_body,
                    color=accent,
                )
                await thread.send(embed=embed, components=[row_btns])
            else:
                await thread.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"# {emoji.correct} Membros Prontos para Entrega!\n"
                                f"-# {emoji.warn} DM fechada — entregando aqui"
                            ),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay(fallback_body),
                            disnake.ui.Separator(),
                            row_btns,
                            accent_colour=accent,
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True),
                )
        except Exception:
            pass

    # Comissão de afiliados
    if valor_pago > 0:
        try:
            from modules.loja.afiliados import helpers as afiliados_helpers
            inviter_id, comissao = afiliados_helpers.registrar_comissao(
                buyer_id=str(user.id),
                valor_compra=valor_pago,
                produto_nome=product_name,
            )
            if inviter_id and comissao > 0:
                print(f"[Afiliados] Comissão R${comissao:.2f} creditada ao afiliado {inviter_id}")
        except Exception as e:
            print(f"[Afiliados] Erro ao registrar comissão (membros): {e}")

    return True  # Entrega de membros é sempre considerada iniciada com sucesso


def _create_stock_file(items: List[str]) -> disnake.File:
    """Cria arquivo .txt com os itens do estoque (apenas conteúdo)"""
    content = "\n".join(items)

    file_buffer = io.BytesIO(content.encode('utf-8'))
    file_buffer.seek(0)
    return disnake.File(file_buffer, filename="seus_itens.txt")


async def deliver_product_to_user(
    user: disnake.User,
    product_name: str,
    campo_name: str,
    quantity: int,
    items: List[str],
    thread: Optional[disnake.Thread] = None,
    guild: Optional[disnake.Guild] = None,
    instructions: Optional[str] = None,
    product_id: Optional[str] = None,
    campo_id: Optional[str] = None
) -> bool:
    """
    Entrega o produto ao usuário via DM
    Retorna True se a entrega foi bem-sucedida
    """
    try:
        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except:
                pass

        # Calcular conteúdo puro (sem numeração) - cada item em uma linha com `
        items_content = "\n".join([f"`{item}`" for item in items])
        content_length = len(items_content)
        
        # Verificar se precisa criar arquivo
        stock_file = None
        use_file = content_length > 2000
        
        # Verificar se deve mostrar botão de copiar (só se conteúdo <= 2000 caracteres)
        show_copy_button = content_length <= 2000

        if use_file:
            stock_file = _create_stock_file(items)
            display_text = f"*Arquivo anexado com {len(items)} item(s)*"
        else:
            display_text = items_content

        if mode == "embed":
            # Modo Embed - mostrar apenas o conteúdo
            embed = disnake.Embed(
                title=f"{emoji.cardbox} Produto Entregue",
                color=color or disnake.Color.green()
            )

            if not use_file:
                embed.add_field(
                    name=f"Seus Itens",
                    value=display_text[:1024],
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"Seus Itens",
                    value=display_text,
                    inline=False
                )

            embed.set_footer(text=f"Obrigado pela compra! {emoji.gift}")
            
            # Adicionar instruções se existirem
            instructions_truncated = None
            if instructions:
                # Truncar instruções para exibição (limite do Discord para embed field value é 1024)
                if len(instructions) > 1024:
                    instructions_truncated = instructions[:1021] + "..."
                else:
                    instructions_truncated = instructions
                embed.add_field(
                    name=f"{emoji.info if hasattr(emoji, 'info') else '📋'} Instruções",
                    value=instructions_truncated,
                    inline=False
                )
            
            # Adicionar botões de copiar
            components = []
            button_row = []
            
            # Botão de copiar conteúdo do produto
            if show_copy_button:
                button_row.append(
                    disnake.ui.Button(
                        label="Copiar Conteúdo",
                        emoji=emoji.cardbox,
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"copy_delivered_content:{user.id}"
                    )
                )
            
            # Botão de copiar instruções (se houver instruções e product_id/campo_id disponíveis)
            if instructions and product_id and campo_id:
                button_row.append(
                    disnake.ui.Button(
                        label="Copiar Instruções",
                        emoji=emoji.info if hasattr(emoji, 'info') else "📋",
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"copy_instructions:{user.id}:{product_id}:{campo_id}"
                    )
                )
            
            if button_row:
                components = [
                    disnake.ui.ActionRow(*button_row)
                ]

            if stock_file:
                await user.send(embed=embed, file=stock_file, components=components if components else None)
            else:
                await user.send(embed=embed, components=components if components else None)

        else:
            # Modo Container - mostrar apenas o conteúdo
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)

            container_items = [
                disnake.ui.TextDisplay(f"# {emoji.cardbox}\n-# Produto Entregue"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"### Seus Itens\n{display_text[:1900]}") if not use_file else disnake.ui.TextDisplay(f"### Seus Itens\n{display_text}")
            ]
            
            # Adicionar instruções se existirem
            instructions_truncated = None
            if instructions:
                container_items.append(disnake.ui.Separator())
                # Truncar instruções para exibição (limite seguro para TextDisplay é ~1900 caracteres)
                if len(instructions) > 1900:
                    instructions_truncated = instructions[:1897] + "..."
                else:
                    instructions_truncated = instructions
                container_items.append(
                    disnake.ui.TextDisplay(f"### {emoji.info if hasattr(emoji, 'info') else '📋'} Instruções\n{instructions_truncated}")
                )
            
            # Adicionar botões de copiar
            button_row = []
            
            # Botão de copiar conteúdo do produto
            if show_copy_button:
                button_row.append(
                    disnake.ui.Button(
                        label="Copiar Conteúdo",
                        emoji=emoji.cardbox,
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"copy_delivered_content:{user.id}"
                    )
                )
            
            # Botão de copiar instruções (se houver instruções e product_id/campo_id disponíveis)
            if instructions and product_id and campo_id:
                button_row.append(
                    disnake.ui.Button(
                        label="Copiar Instruções",
                        emoji=emoji.info if hasattr(emoji, 'info') else "📋",
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"copy_instructions:{user.id}:{product_id}:{campo_id}"
                    )
                )
            
            if button_row:
                container_items.append(
                    disnake.ui.ActionRow(*button_row)
                )

            components = [
                disnake.ui.Container(
                    *container_items,
                    **container_kwargs
                )
            ]

            # Enviar container primeiro
            await user.send(components=components, flags=disnake.MessageFlags(is_components_v2=True))
            
            # Enviar arquivo separadamente se necessário (components v2 não aceita files)
            if stock_file:
                await user.send(file=stock_file)

        # Enviar mensagem de incentivo de feedback
        await _send_feedback_incentive(user, guild)

        # Enviar painel de avaliação 5 estrelas (por último, após todo o conteúdo)
        if guild:
            try:
                from modules.loja.preferences.cinco_estrelas import send_rating_dm
                await send_rating_dm(
                    user=user,
                    product_name=product_name,
                    campo_name=campo_name,
                    guild_id=guild.id,
                )
            except Exception as e:
                print(f"[5 ESTRELAS] Erro ao enviar DM de avaliação: {e}")

        # Se houver thread, enviar confirmação (content simples)
        # Não enviar aqui - será enviado em _handle_payment_approved como reply

        return True

    except disnake.Forbidden:
        # Usuário bloqueou DMs - Entregar no carrinho (content simples)
        if thread:
            # Calcular conteúdo puro (sem numeração) - cada item em uma linha com `
            items_content = "\n".join([f"`{item}`" for item in items])
            content_length = len(items_content)
            use_file = content_length > 2000
            
            if use_file:
                stock_file = _create_stock_file(items)
                display_text = f"*Arquivo anexado com {len(items)} item(s)*"
            else:
                stock_file = None
                display_text = items_content
            
            # Avisar que a DM está fechada
            await thread.send(
                f"{emoji.warn} **DM Fechada**\n{user.mention}, suas mensagens diretas estão desativadas!\nOs itens serão entregues aqui no carrinho."
            )
            
            # Entregar os itens no carrinho (apenas conteúdo)
            delivery_message = f"# {emoji.correct} **Produto Entregue!**\n\n"
            
            if use_file:
                delivery_message += f"**Seus Itens:** *Arquivo anexado com {len(items)} item(s)*"
            else:
                delivery_message += f"**Seus Itens:**\n{display_text}"
            
            # Adicionar instruções se existirem
            if instructions:
                delivery_message += f"\n\n**Instruções:**\n{instructions}"
            
            if use_file:
                await thread.send(
                    content=delivery_message,
                    file=stock_file
                )
            else:
                await thread.send(content=delivery_message)
            
            return True  # Entrega bem-sucedida no carrinho
        
        return False

    except Exception as e:
        if thread:
            # Mensagem de erro (content simples)
            await thread.send(
                f"{emoji.wrong} **Erro na Entrega**\nErro ao entregar produto: {str(e)}"
            )
        return False


async def _send_feedback_incentive(user: disnake.User, guild: Optional[disnake.Guild]):
    """Envia mensagem de incentivo de feedback"""
    try:
        config = db.get_document("loja_personalization") or {}
        feedback_config = config.get("feedback_incentive", {})

        if not feedback_config.get("message"):
            return

        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except:
                pass

        message_text = feedback_config.get("message", "")
        button_text = feedback_config.get("button_text", "Deixar Avaliação")

        # Obter canal de avaliações se existir
        canais = db.get_document("canais") or {}
        feedback_channel_id = canais.get("canal_de_feedback")

        components_list = []
        if feedback_channel_id and guild:
            feedback_url = f"https://discord.com/channels/{guild.id}/{feedback_channel_id}"
            components_list = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label=button_text,
                        style=disnake.ButtonStyle.link,
                        url=feedback_url,
                        emoji=emoji.star
                    )
                )
            ]

        if mode == "embed":
            embed = disnake.Embed(
                description=message_text,
                color=color or disnake.Color.blurple()
            )
            await user.send(embed=embed, components=components_list if components_list else None)
        else:
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)

            main_components = [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(message_text),
                    **container_kwargs
                )
            ]

            if components_list:
                main_components.extend(components_list)

            await user.send(components=main_components, flags=disnake.MessageFlags(is_components_v2=True))

    except Exception:
        pass


async def deliver_boost_to_user(
    user: disnake.User,
    product_name: str,
    campo_name: str,
    gift_id: str,
    gift_url: str,
    boost_count,
    thread: Optional[disnake.Thread] = None,
    guild: Optional[disnake.Guild] = None,
) -> bool:
    """
    Entrega um gift de boost ao usuário via DM com link de resgate.
    O cliente clica no link e as contas vinculadas executam o boost automaticamente.
    """
    try:
        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except Exception:
                pass

        boost_count_str = str(boost_count)
        msg_text = (
            f"Seu pedido de **{campo_name}** foi processado com sucesso!\n\n"
            f"**Como resgatar:**\n"
            f"-# 1. Clique no botão abaixo para abrir o link de resgate\n"
            f"-# 2. Confirme no servidor de boost\n"
            f"-# 3. As `{boost_count_str}` contas irão impulsionar seu servidor automaticamente\n\n"
            f"**Gift ID:** `{gift_id}`"
        )

        view_button = disnake.ui.Button(
            label=f"Resgatar {boost_count_str}x Boost",
            style=disnake.ButtonStyle.link,
            url=gift_url,
            emoji="⚡",
        )

        if mode == "embed":
            embed = disnake.Embed(
                title=f"⚡ {product_name}",
                description=msg_text,
                color=color or disnake.Color.blurple(),
            )
            embed.set_footer(text="Obrigado pela compra!")
            components = [disnake.ui.ActionRow(view_button)]
            await user.send(embed=embed, components=components)
        else:
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)
            await user.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# ⚡ {product_name}\n-# Produto Entregue"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(msg_text),
                        disnake.ui.ActionRow(view_button),
                        **container_kwargs,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )

        # Incentivo de feedback
        await _send_feedback_incentive(user, guild)

        # Painel de avaliação
        if guild:
            try:
                from modules.loja.preferences.cinco_estrelas import send_rating_dm
                await send_rating_dm(user, guild)
            except Exception:
                pass

        return True

    except disnake.Forbidden:
        return False
    except Exception as e:
        print(f"[Delivery] Erro ao entregar boost: {e}")
        return False


async def process_automatic_delivery(
    user: disnake.User,
    product_id: str,
    campo_id: str,
    product_name: str,
    campo_name: str,
    quantity: int,
    thread: Optional[disnake.Thread] = None,
    guild: Optional[disnake.Guild] = None,
    valor_pago: float = 0.0,
    owner_bot_id: Optional[str] = None,
) -> bool:
    """
    Processa a entrega automática de um produto.
    Retorna True se a entrega foi bem-sucedida.

    owner_bot_id: quando informado, busca o produto/campo/estoque na collection
    do bot dono (produto revendido) em vez da collection local.
    """

    # ── Entrega especial: produto de membros AmyCloud ─────────────────────────
    if campo_id == "__members__":
        cart_id = str(thread.id) if thread else "unknown"
        return await deliver_members_to_user(
            user=user,
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            cart_id=cart_id,
            thread=thread,
            guild=guild,
            valor_pago=valor_pago,
        )
    # ─────────────────────────────────────────────────────────────────────────

    # ── Buscar produto/campo — local ou cross-bot ─────────────────────────────
    if owner_bot_id:
        # Produto revendido: buscar na collection do bot dono
        from connections.mongo_db import database as mongo_database
        _owner_col = mongo_database[owner_bot_id]
        _raw = _owner_col.find_one({"_id": "loja_products"}) or {}
        _raw.pop("_id", None)
        product = _raw.get(product_id, {})
    else:
        products = db.get_document("loja_products")
        product = products.get(product_id, {})

    campo = product.get("campos", {}).get(campo_id, {})
    
    # ── Lógica de Assinatura ──────────────────────────────────────────────────
    if campo.get("is_subscription"):
        from .subscription_manager import SubscriptionManager
        success = await SubscriptionManager.activate_subscription(
            user=user,
            product_id=product_id,
            campo_id=campo_id,
            product_name=product_name,
            campo_name=campo_name,
            guild=guild,
            thread=thread
        )
        
        if success and valor_pago > 0:
            try:
                from modules.loja.afiliados import helpers as afiliados_helpers
                inviter_id, comissao = afiliados_helpers.registrar_comissao(
                    buyer_id=str(user.id),
                    valor_compra=valor_pago,
                    produto_nome=product_name,
                )
                if inviter_id and comissao > 0:
                    print(f"[Afiliados] Comissão R${comissao:.2f} creditada ao afiliado {inviter_id}")
            except Exception as e:
                print(f"[Afiliados] Erro ao registrar comissão: {e}")
        return success
    # ─────────────────────────────────────────────────────────────────────────

    # ── Retirar itens do estoque — local ou cross-bot ─────────────────────────
    if owner_bot_id:
        import asyncio
        from functions.stock_request_client import request_stock_items
        items = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: request_stock_items(owner_bot_id, product_id, campo_id, quantity)
        )
    else:
        items = StockManager.get_stock_items(product_id, campo_id, quantity)

    if items is None:
        # Sem estoque suficiente
        if thread:
            mode = (db.get_document("custom_mode") or {}).get("mode", "components")
            if mode == "embed":
                error_embed = disnake.Embed(
                    title=f"{emoji.wrong} Estoque Insuficiente",
                    description=(
                        f"Não há estoque suficiente para entregar este produto.\n"
                        f"Por favor, entre em contato com um administrador."
                    ),
                    color=disnake.Color.red()
                )
                await thread.send(embed=error_embed)
            else:
                await thread.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.wrong} Estoque Insuficiente"),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay(
                                f"Não há estoque suficiente para entregar este produto.\n"
                                f"Por favor, entre em contato com um administrador."
                            ),
                            accent_colour=disnake.Colour.red()
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
        return False

    # ── Verificar se é entrega de boost (marcador especial) ──────────────────
    if items and items[0].startswith("__BOOST_GIFT__"):
        marker = items[0]  # __BOOST_GIFT__{gift_id}__{boost_count}
        parts = marker.split("__")
        # partes: ['', 'BOOST_GIFT', gift_id, boost_count, ''] dependendo da string
        gift_id = parts[2] if len(parts) > 2 else "?"
        boost_count = parts[3] if len(parts) > 3 else "?"
        gift_url = f"https://boost.syncapplications.com.br/gifts/{gift_id}"
        success = await deliver_boost_to_user(
            user=user,
            product_name=product_name,
            campo_name=campo_name,
            gift_id=gift_id,
            gift_url=gift_url,
            boost_count=boost_count,
            thread=thread,
            guild=guild,
        )
        if success and valor_pago > 0:
            try:
                from modules.loja.afiliados import helpers as afiliados_helpers
                inviter_id, comissao = afiliados_helpers.registrar_comissao(
                    buyer_id=str(user.id),
                    valor_compra=valor_pago,
                    produto_nome=product_name,
                )
                if inviter_id and comissao > 0:
                    print(f"[Afiliados] Comissão R${comissao:.2f} creditada ao afiliado {inviter_id}")
            except Exception as e:
                print(f"[Afiliados] Erro ao registrar comissão: {e}")
        return success
    # ─────────────────────────────────────────────────────────────────────────

    # Buscar instruções do campo
    products = db.get_document("loja_products")
    product = products.get(product_id, {})
    campo = product.get("campos", {}).get(campo_id, {})
    instructions = campo.get("instructions")
    
    # Entregar ao usuário
    success = await deliver_product_to_user(
        user=user,
        product_name=product_name,
        campo_name=campo_name,
        quantity=quantity,
        items=items,
        thread=thread,
        guild=guild,
        instructions=instructions,
        product_id=product_id,
        campo_id=campo_id
    )

    if not success:
        # Devolver itens ao estoque
        StockManager.return_stock_items(product_id, campo_id, items)
        return False

    # ── Comissão de afiliados ─────────────────────────────────────────────────
    if valor_pago > 0:
        try:
            from modules.loja.afiliados import helpers as afiliados_helpers
            inviter_id, comissao = afiliados_helpers.registrar_comissao(
                buyer_id=str(user.id),
                valor_compra=valor_pago,
                produto_nome=product_name,
            )
            if inviter_id and comissao > 0:
                print(f"[Afiliados] Comissão R${comissao:.2f} creditada ao afiliado {inviter_id}")
        except Exception as e:
            print(f"[Afiliados] Erro ao registrar comissão: {e}")
    # ─────────────────────────────────────────────────────────────────────────

    # Logs são enviados centralmente em _handle_payment_approved para evitar duplicação
    # Não enviar logs aqui para evitar duplicação quando há múltiplos produtos no carrinho
    
    return success


async def send_payment_approved_dm(
    user: disnake.User,
    product_name: str,
    campo_name: str,
    quantity: int,
    delivery_type: str,
    thread_url: Optional[str] = None
):
    """Envia DM informando que o pagamento foi aprovado"""
    try:
        mode = (db.get_document("custom_mode") or {}).get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        color = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except:
                pass

        delivery_text = ""
        if delivery_type == "automatic":
            delivery_text = "Seu produto será entregue automaticamente em instantes!"
        else:
            delivery_text = f"Entrega manual. Um administrador irá entregar seu produto em breve.\nAcompanhe no carrinho: {thread_url if thread_url else 'Verifique o servidor'}"

        if mode == "embed":
            embed = disnake.Embed(
                title=f"{emoji.correct} Pagamento Aprovado!",
                description=(
                    f"Seu pagamento foi aprovado com sucesso!\n\n"
                    f"**Produto:** {product_name}\n"
                    f"**Campo:** {campo_name}\n"
                    f"**Quantidade:** {quantity}"
                ),
                color=color or disnake.Color.green()
            )

            embed.add_field(
                name="Entrega",
                value=delivery_text,
                inline=False
            )

            await user.send(embed=embed)

        else:
            container_kwargs = {}
            if color:
                container_kwargs["accent_colour"] = disnake.Colour(color)

            await user.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.correct} Pagamento Aprovado!"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"Seu pagamento foi aprovado com sucesso!\n\n"
                            f"**Produto:** {product_name}\n"
                            f"**Campo:** {campo_name}\n"
                            f"**Quantidade:** {quantity}"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"**Entrega:** {delivery_text}"),
                        **container_kwargs
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
            )

    except disnake.Forbidden:
        pass  # Usuário bloqueou DMs
    except Exception:
        pass  # Ignorar outros erros