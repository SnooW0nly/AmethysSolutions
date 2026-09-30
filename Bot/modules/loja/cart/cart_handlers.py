"""
Handlers para botões do carrinho de compras
"""
import disnake
import asyncio
import io
from disnake.ext import commands
from datetime import datetime
from typing import Optional, Dict, Any
from functions.database import database as db
from functions.emoji import emoji
from .checkout import _build_cart_message, _add_item_to_cart, _create_payment, _extract_urls, _extract_qr_image, _extract_payment_ids, _http_get_bytes, _api_base_root
from .coupon_validator import CouponValidator
from .cart_utils import get_available_payment_methods, ensure_emoji
from .stock_manager import StockManager


class CartPaymentMethodModal(disnake.ui.Modal):
    """Modal para seleção do método de pagamento do carrinho."""
    
    def __init__(self, cart_id: str):
        self.cart_id = str(cart_id)
        
        available_methods = get_available_payment_methods()
        components = []
        
        if available_methods:
            options = []
            for method_key, method_info in available_methods.items():
                payment_emoji = ensure_emoji(method_info["emoji"])
                options.append(
                    disnake.SelectOption(
                        label=method_info["label"],
                        value=method_key,
                        description=method_info["description"],
                        emoji=payment_emoji,
                    )
                )
            
            components.append(
                disnake.ui.Label(
                    text="Método de Pagamento",
                    component=disnake.ui.StringSelect(
                        placeholder="Selecione o método de pagamento",
                        custom_id="payment_method",
                        options=options,
                        required=True,
                    ),
                    description="Escolha como deseja pagar o carrinho",
                )
            )
        
        super().__init__(
            title="Escolher Forma de Pagamento",
            components=components,
            custom_id=f"cart_payment_modal:{self.cart_id}",
        )
    
    async def callback(self, inter: disnake.ModalInteraction):
        """Atualiza o método de pagamento do carrinho."""
        # Evitar timeout: defer logo no início
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)

        custom_id = inter.custom_id or ""
        parts = custom_id.split(":")
        cart_id = parts[1] if len(parts) >= 2 else None
        if not cart_id:
            await inter.followup.send(
                f"{emoji.wrong} Carrinho não encontrado.",
                ephemeral=True,
            )
            return
        
        valores = inter.resolved_values
        payment_value = valores.get("payment_method")
        
        if isinstance(payment_value, (list, tuple)):
            payment_method = payment_value[0] if payment_value else None
        else:
            payment_method = payment_value or None
        
        if not payment_method:
            await inter.followup.send(
                f"{emoji.wrong} Selecione um método de pagamento válido.",
                ephemeral=True,
            )
            return
        
        # Carregar carrinho
        loja_data = db.get_document("loja_data")
        cart = loja_data.get("carts", {}).get(cart_id)
        
        if not cart:
            await inter.followup.send(
                f"{emoji.wrong} Carrinho não encontrado!",
                ephemeral=True,
            )
            return
        
        if cart.get("user_id") != inter.user.id:
            await inter.followup.send(
                f"{emoji.wrong} Este não é o seu carrinho!",
                ephemeral=True,
            )
            return
        
        # Atualizar método de pagamento
        cart["payment_method"] = payment_method
        cart["updated_at"] = int(datetime.utcnow().timestamp())
        
        loja_data["carts"][cart_id] = cart
        db.save_document("loja_data", loja_data)
        
        # Atualizar mensagem do carrinho
        thread_id = cart.get("thread_id")
        thread = inter.guild.get_thread(thread_id) if thread_id else None
        if thread:
            mode = db.get_document("custom_mode").get("mode", "embed")
            cart_msg_id = cart.get("cart_message_id")
            if cart_msg_id:
                try:
                    cart_msg = await thread.fetch_message(cart_msg_id)
                    new_cart_msg = await _build_cart_message(cart, thread, mode)
                    await cart_msg.delete()
                    cart["cart_message_id"] = new_cart_msg.id
                    loja_data["carts"][cart_id] = cart
                    db.save_document("loja_data", loja_data)
                except Exception:
                    pass
        
        method_names = {"pix": "PIX", "card": "Cartão de Crédito", "crypto": "Criptomoeda"}
        pretty_name = method_names.get(payment_method, payment_method.upper())
        
        await inter.followup.send(
            f"{emoji.correct} Método de pagamento atualizado para `{pretty_name}`!",
            ephemeral=True,
        )


class CartButtonHandlers(commands.Cog):
    """Handlers para botões do carrinho"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener("on_button_click")
    async def on_cart_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        # Guard: ignora qualquer botão que não seja do carrinho
        if not custom_id or not custom_id.startswith("cart_"):
            return

        # ── DEFER IMEDIATO ──────────────────────────────────────────────────────
        # Botões que abrem modal NÃO podem ser deferidos antes — tratados separado.
        # Todos os outros recebem defer imediato para evitar Unknown Interaction (10062).
        _modal_buttons = (
            "cart_change_payment:",
            "cart_edit_quantity:",
            "cart_apply_coupon:",
        )
        _needs_modal = any(custom_id.startswith(p) for p in _modal_buttons)
        if not _needs_modal and not inter.response.is_done():
            try:
                await inter.response.defer(ephemeral=True)
            except Exception:
                pass
        # ───────────────────────────────────────────────────────────────────────

        # Handler para alterar método de pagamento do carrinho
        if custom_id.startswith("cart_change_payment:"):
            thread_id = int(custom_id.split(":")[1])
            cart_id = str(thread_id)
            
            # Verificar métodos disponíveis primeiro (operação rápida)
            available_methods = get_available_payment_methods()
            if not available_methods:
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            f"{emoji.wrong} Nenhum método de pagamento está disponível no momento. Entre em contato com um administrador.",
                            ephemeral=True
                        )
                    else:
                        await inter.followup.send(
                            f"{emoji.wrong} Nenhum método de pagamento está disponível no momento. Entre em contato com um administrador.",
                            ephemeral=True
                        )
                except:
                    pass
                return
            
            # Criar modal (operação rápida)
            modal = CartPaymentMethodModal(cart_id)
            
            # Tentar abrir modal imediatamente
            try:
                if not inter.response.is_done():
                    await inter.response.send_modal(modal)
                else:
                    # Se já foi respondida, não podemos enviar modal
                    await inter.followup.send(
                        f"{emoji.wrong} Não foi possível abrir o modal. Tente novamente.",
                        ephemeral=True
                    )
            except disnake.errors.NotFound:
                # Interação expirou - tentar enviar mensagem de erro
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            f"{emoji.wrong} A interação expirou. Por favor, tente novamente.",
                            ephemeral=True
                        )
                    else:
                        await inter.followup.send(
                            f"{emoji.wrong} A interação expirou. Por favor, tente novamente.",
                            ephemeral=True
                        )
                except:
                    pass
            except Exception as e:
                # Outro erro - tentar enviar mensagem de erro
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            f"{emoji.wrong} Erro ao abrir modal: {str(e)}",
                            ephemeral=True
                        )
                    else:
                        await inter.followup.send(
                            f"{emoji.wrong} Erro ao abrir modal: {str(e)}",
                            ephemeral=True
                        )
                except:
                    pass
            return
        
        # Handler para continuar com o carrinho (criar pagamento)
        if custom_id.startswith("cart_continue:"):
            thread_id = int(custom_id.split(":")[1])
            cart_id = str(thread_id)

            # Editar a mensagem do carrinho NA THREAD para mostrar loading e remover botões.
            # Isso impede o usuário de clicar novamente enquanto processa.
            # NÃO usar defer aqui — edit_message já responde a interação.
            if not inter.response.is_done():
                try:
                    await inter.response.edit_message(
                        content="⏳ Processando pagamento, aguarde...",
                        embed=None,
                        components=[],
                        attachments=[]
                    )
                except Exception:
                    # Fallback: defer normal se edit_message falhar
                    try:
                        await inter.response.defer(ephemeral=True)
                    except Exception:
                        pass
            
            # Carregar carrinho (recarregar do banco para garantir dados atualizados)
            loja_data = db.get_document("loja_data")
            carts_available = list(loja_data.get("carts", {}).keys())
            
            cart = loja_data.get("carts", {}).get(cart_id)
            
            # Se não encontrou, tentar migrar se necessário
            if not cart:
                # Tentar buscar por thread_id como int também
                cart = loja_data.get("carts", {}).get(str(thread_id))
                if not cart:
                    # Tentar buscar por thread_id como int
                    for key, value in loja_data.get("carts", {}).items():
                        if value.get("thread_id") == thread_id:
                            cart = value
                            cart_id = key  # Atualizar cart_id para a chave correta
                            break
            
            if not cart:
                await inter.followup.send(
                    f"{emoji.wrong} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            # Migrar carrinho se necessário
            from .checkout import _migrate_cart_to_items
            cart = _migrate_cart_to_items(cart)
            
            # Salvar carrinho migrado se necessário
            if cart_id not in loja_data.get("carts", {}):
                loja_data["carts"][cart_id] = cart
                db.save_document("loja_data", loja_data)
            
            
            # Verificar se é o dono do carrinho
            if cart.get("user_id") != inter.user.id:
                await inter.followup.send(
                    f"{emoji.wrong} Este não é o seu carrinho!",
                    ephemeral=True
                )
                return
            
            # Verificar se já está em pagamento
            if cart.get("status") != "cart":
                await inter.followup.send(
                    f"{emoji.wrong} Este carrinho já está em processo de pagamento!",
                    ephemeral=True
                )
                return
            
            items = cart.get("items", [])
            if not items:
                await inter.followup.send(
                    f"{emoji.wrong} Carrinho vazio!",
                    ephemeral=True
                )
                return
            
            # Verificar estoque ANTES de criar pagamento
            products = db.get_document("loja_products")
            stock_errors = []
            no_stock_items = []  # Itens completamente sem estoque (para botões de notificação)
            
            for item in items:
                product_id = item.get("product_id")
                campo_id = item.get("campo_id")
                quantity = item.get("quantity", 1)
                
                if not product_id or not campo_id:
                    continue
                
                product = products.get(product_id, {})
                if not product:
                    continue
                
                campos = product.get("campos", {})
                campo = campos.get(campo_id, {})
                if not campo:
                    continue
                
                info = product.get("info", {})
                delivery_type = info.get("delivery_type", "automatic")
                
                # Verificar se é estoque infinito
                infinite_stock = campo.get("infinite_stock", {})
                is_infinite = infinite_stock.get("enabled", False)
                
                if not is_infinite and delivery_type == "automatic":
                    # Verificar estoque disponível
                    stock_count = StockManager.get_available_stock(product_id, campo_id)
                    
                    if stock_count < quantity:
                        product_name = product.get("name", "Produto")
                        campo_name = campo.get("name", "Campo")
                        
                        if stock_count <= 0:
                            # Sem estoque - adicionar para mostrar botão de notificação
                            no_stock_items.append({
                                "product_id": product_id,
                                "campo_id": campo_id,
                                "product_name": product_name,
                                "campo_name": campo_name
                            })
                            stock_errors.append(f"**{product_name}** - `{campo_name}`: Sem estoque disponível")
                        else:
                            stock_errors.append(f"**{product_name}** - `{campo_name}`: Estoque insuficiente (disponível: {stock_count}, necessário: {quantity})")
            
            if stock_errors:
                error_msg = f"{emoji.wrong} **Estoque insuficiente para alguns produtos:**\n\n" + "\n".join(stock_errors)
                
                # Adicionar botões de notificação para produtos sem estoque
                components = []
                if no_stock_items:
                    # Limitar a 5 botões (máximo por ActionRow)
                    buttons = []
                    for no_stock_item in no_stock_items[:5]:
                        notify_emoji = ensure_emoji(emoji.warn)
                        buttons.append(
                            disnake.ui.Button(
                                emoji=notify_emoji,
                                label=f"Notificar: {no_stock_item['product_name']}",
                                style=disnake.ButtonStyle.grey,
                                custom_id=f"notify_stock:{no_stock_item['product_id']}:{no_stock_item['campo_id']}"
                            )
                        )
                    
                    if buttons:
                        components.append(disnake.ui.ActionRow(*buttons))
                
                await inter.followup.send(
                    error_msg,
                    components=components if components else None,
                    ephemeral=True
                )
                return
            
            # Verificar se está em manutenção
            from modules.loja.preferences.utils import check_maintenance
            is_maintenance, maintenance_msg = check_maintenance(inter.user.id, inter.guild)
            if is_maintenance:
                await inter.followup.send(
                    maintenance_msg or "🔧 Sistema em manutenção. Por favor, tente novamente mais tarde.",
                    ephemeral=True
                )
                return
            
            # Verificar horário de funcionamento
            from modules.loja.preferences.utils import check_store_hours
            is_open, hours_msg = check_store_hours()
            if not is_open:
                await inter.followup.send(
                    hours_msg or "⏰ A loja está fora do horário de funcionamento.",
                    ephemeral=True
                )
                return
            
            # Verificar termos (se não foram aceitos ainda)
            from modules.loja.preferences.utils import get_terms
            terms_enabled, terms_text = get_terms()
            if terms_enabled and not cart.get("terms_accepted", False):
                # Mostrar modal de aceitação de termos
                # Criar modal ANTES de qualquer outra operação para evitar timeout
                from modules.loja.cart.terms_modal import TermsAcceptanceModal
                modal = TermsAcceptanceModal(cart_id)
                
                # Após defer, não é possível enviar modal — informar usuário via followup
                try:
                    await inter.followup.send(
                        f"{emoji.wrong} Você precisa aceitar os Termos de Serviço antes de continuar. Por favor, clique em **Continuar** novamente para aceitar os termos.",
                        ephemeral=True
                    )
                except Exception as e:
                    pass
                return
            
            # Calcular total
            total_price = sum(item.get("item_total", 0) for item in items)
            payment_method = cart.get("payment_method", "pix")
            
            # Obter cupom do carrinho (se aplicado)
            discount_amount = cart.get("discount_amount", 0) or 0
            coupon_applied = cart.get("coupon_code")
            coupon_type = cart.get("coupon_type")
            is_free_purchase = cart.get("is_free_purchase", False)
            
            final_price = max(0, total_price - discount_amount)

            # ── Taxa de transação Amethys Wallet ─────────────────────────────
            # Verificar se Amethys Wallet está ativo e se cliente paga a taxa
            _amethys_fee_added = 0.0
            pagamentos_doc = db.get_document("pagamentos") or {}
            payment_configs_doc = db.get_document("payment_configs") or {}
            _amethys_cfg = payment_configs_doc.get("amethys_wallet") or {}
            _amethys_enabled = pagamentos_doc.get("amethys_wallet", False)
            _customer_pays_fee = _amethys_cfg.get("customer_pays_fee", False)

            if _amethys_enabled and _customer_pays_fee and payment_method == "pix" and final_price > 0:
                try:
                    from functions.payments.amethys_wallet import _request, _get_api_key
                    _api_key = _get_api_key()
                    _plan_result = await _request("GET", "api/v1/user/my-plan", api_key=_api_key)
                    _plan_data = _plan_result.get("data", {}).get("currentPlan", {})

                    _mistic_fixed = 0.50  # R$ 0,50 fixo da Mistic — imutavel

                    # Plano da ApiKey: somente % por transacao (WHITE=4%, BLACK=6%)
                    _fee_percent = float(_plan_data.get("transactionFeePercent") or 0)

                    # Taxa da plataforma: so % sobre o valor
                    _platform_fee = round(final_price * _fee_percent / 100, 2)
                    # Taxa total repassada ao cliente: % da plataforma + R$ 0,50 fixo da Mistic
                    _amethys_fee_added = round(_platform_fee + _mistic_fixed, 2)
                    final_price = round(final_price + _amethys_fee_added, 2)
                    print(f"[CART] Taxa Amethys adicionada ao cliente: R$ {_amethys_fee_added:.2f} ({_fee_percent}% = R$ {_platform_fee:.2f} + Mistic R$ {_mistic_fixed:.2f}) | Novo total: R$ {final_price:.2f}")
                except Exception as _fee_err:
                    print(f"[CART] Erro ao buscar taxa do plano Amethys: {_fee_err}")
            # ─────────────────────────────────────────────────────────────────

            # ── Validação para carrinhos de revenda ──────────────────────────
            # Amethys Wallet é obrigatória para carrinhos de revenda (split de comissão)
            resale_info = cart.get("resale_info")
            if resale_info:
                _pagamentos_check = db.get_document("pagamentos") or {}
                _configs_check = db.get_document("payment_configs") or {}
                _aw_cfg = _configs_check.get("amethys_wallet") or {}
                _aw_enabled = _pagamentos_check.get("amethys_wallet", False)
                _aw_key = _aw_cfg.get("api_key")
                if not _aw_enabled or not _aw_key:
                    await inter.followup.send(
                        f"{emoji.wrong} Este produto é revendido e requer **Amethys Wallet** configurada e ativa neste bot para processar o split de comissão.\n"
                        f"{emoji.arrow} Entre em contato com um administrador.",
                        ephemeral=True,
                    )
                    return

                # Verificar Amethys Wallet do bot dono do produto (cross-bot via MongoDB)
                _owner_bot_id = resale_info.get("bot_id")
                if _owner_bot_id:
                    from functions.marketplace import get_owner_amethys_config
                    _owner_aw_cfg = get_owner_amethys_config(_owner_bot_id)
                    if not _owner_aw_cfg:
                        await inter.followup.send(
                            f"{emoji.wrong} O bot dono deste produto não possui **Amethys Wallet** configurada.\n"
                            f"{emoji.arrow} O split de comissão não pode ser processado no momento.",
                            ephemeral=True,
                        )
                        return
                    # Salvar api_key do dono no resale_info do carrinho para uso no checkout
                    loja_data = db.get_document("loja_data")
                    if cart_id in loja_data.get("carts", {}):
                        loja_data["carts"][cart_id]["resale_info"]["owner_amethys_api_key"] = _owner_aw_cfg["api_key"]
                        db.save_document("loja_data", loja_data)

                # Forçar pagamento via pix (único método suportado pela Amethys Wallet para revenda)
                if payment_method != "pix":
                    await inter.followup.send(
                        f"{emoji.wrong} Produtos revendidos só aceitam pagamento via **PIX** (Amethys Wallet).",
                        ephemeral=True,
                    )
                    return
            # ─────────────────────────────────────────────────────────────────

            # Validar valor mínimo para pagamento PIX
            if payment_method == "pix" and final_price < 0.50:
                await inter.followup.send(
                    f"{emoji.wrong} O valor mínimo para pagamento via PIX é R$ 0,50.\n"
                    f"{emoji.arrow} Valor atual: R$ {final_price:.2f}\n\n"
                    f"Por favor, adicione mais itens ao carrinho ou remova o cupom.",
                    ephemeral=True
                )
                return
            
            # Criar pagamento
            try:
                # Criar descrição
                products = db.get_document("loja_products")
                descriptions = []
                for item in items:
                    product = products.get(item.get("product_id"))
                    if product:
                        product_name = product.get("name", "Produto")
                        campos = product.get("campos", {})
                        campo = campos.get(item.get("campo_id"))
                        campo_name = campo.get("name", "") if campo else "Campo"
                        quantity = item.get("quantity", 1)
                        descriptions.append(f"{product_name} - {campo_name} x{quantity}")
                
                description = " | ".join(descriptions)
                
                # Efi Bank agora NÃO precisa de CPF e nome - API gera automaticamente
                # Criar pagamento diretamente
                
                print(f"[CART] Criando pagamento: method={payment_method}, amount={final_price}, description={description}")
                
                payment_data = await _create_payment(
                    payment_method=payment_method,
                    amount=final_price,
                    user=inter.user,
                    description=description
                )
                
                print(f"[CART] Pagamento criado com sucesso: {payment_data.keys() if payment_data else 'None'}")
            except Exception as e:
                print(f"[CART] Erro ao criar pagamento: {e}")
                import traceback
                traceback.print_exc()
                
                nice_names = {"pix": "PIX", "card": "Cartão de Crédito", "crypto": "Criptomoeda"}
                method_pretty = nice_names.get(payment_method, payment_method.upper())
                await inter.followup.send(
                    content=(
                        f"{emoji.wrong} Não há nenhuma forma de pagamento configurada para {method_pretty}.\n"
                        f"{emoji.arrow} Por favor, contate um administrador."
                    ),
                    ephemeral=True
                )
                return
            
            # Extrair informações do pagamento
            checkout_url, copy_code = _extract_urls(payment_data or {})
            qr_bytes, qr_url = _extract_qr_image(payment_data or {})
            
            if not qr_bytes and payment_data and payment_data.get("qr_code_bytes"):
                qr_bytes = payment_data.get("qr_code_bytes")
            
            if not copy_code and payment_data:
                copy_code = payment_data.get("pix_copia_cola") or payment_data.get("copy_paste") or payment_data.get("emv")
            
            payment_ids = _extract_payment_ids(payment_data or {})
            requires_manual_approval = payment_data.get("requires_manual_approval", False) if payment_data else False
            payment_provider = payment_data.get("_provider") if payment_data else None
            
            # Se tiver URL do QR Code, tentar baixar os bytes
            if qr_url:
                base_root = _api_base_root()
                full_url = str(qr_url)
                if full_url.startswith("/"):
                    full_url = base_root + full_url
                fetched = await _http_get_bytes(full_url)
                if fetched:
                    qr_bytes = fetched
                    qr_url = None
            
            # Obter thread
            thread = inter.guild.get_thread(thread_id)
            if not thread:
                await inter.followup.send(
                    f"{emoji.wrong} Thread não encontrada!",
                    ephemeral=True
                )
                return
            
            # Formatar preços
            if discount_amount > 0:
                original_price_str = f"R$ {total_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                final_price_str = f"R$ {final_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                discount_str = f"R$ {discount_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                price_display = f"~~{original_price_str}~~ → **{final_price_str}**\nDesconto: {discount_str}"
                if coupon_applied:
                    price_display += f"\n{emoji.coupon} Cupom: `{coupon_applied}`"
            else:
                price_display = f"R$ {final_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            # Método de pagamento
            method_names = {
                "pix": "PIX",
                "card": "Cartão de Crédito",
                "crypto": "Criptomoeda"
            }
            payment_method_display = method_names.get(payment_method, payment_method.upper())
            
            # Preparar componentes
            components = []
            main_row = []
            
            # Botão Copiar Código PIX
            if copy_code:
                main_row.append(
                    disnake.ui.Button(
                        label="PIX Cópia e Cola",
                        emoji=emoji.pix if hasattr(emoji, 'pix') else "💳",
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"copy_pix:{thread_id}"
                    )
                )
            
            # Botão Cancelar na mesma linha
            main_row.append(
                disnake.ui.Button(
                    label="Cancelar",
                    emoji=emoji.delete,
                    style=disnake.ButtonStyle.danger,
                    custom_id=f"cancel_checkout:{thread_id}"
                )
            )
            
            # Adicionar linha principal
            if main_row:
                components.append(disnake.ui.ActionRow(*main_row))
            
            # Botão de Aprovar Pagamento (se necessário) em linha separada
            if requires_manual_approval:
                components.append(
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Aprovar Pagamento",
                            emoji=emoji.double_check if hasattr(emoji, 'double_check') else "✅",
                            style=disnake.ButtonStyle.success,
                            custom_id=f"approve_manual_pix:{thread_id}"
                        )
                    )
                )
            
            # Preparar arquivos (QR Code)
            files = []
            qr_attachment_url = None
            
            if qr_bytes:
                file = disnake.File(io.BytesIO(qr_bytes), filename="qrcode.png")
                files.append(file)
                qr_attachment_url = "attachment://qrcode.png"
            elif qr_url:
                qr_attachment_url = qr_url
            
            # Obter cor do produto
            product_color = None
            if items:
                first_item = items[0]
                product = products.get(first_item.get("product_id"))
                if product and product.get("color"):
                    try:
                        product_color_hex = product.get("color")
                        if product_color_hex.startswith("#"):
                            product_color = disnake.Colour(int(product_color_hex.replace("#", ""), 16))
                        else:
                            product_color = disnake.Colour(int(product_color_hex, 16))
                    except:
                        pass
            
            # Enviar mensagem de pagamento
            mode = db.get_document("custom_mode").get("mode", "embed")
            
            if mode == "components":
                container_components = []
                container_components.append(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Checkout")
                )
                container_components.append(disnake.ui.Separator())
                
                # Listar produtos
                for item in items:
                    product = products.get(item.get("product_id"))
                    if not product:
                        continue
                    product_name = product.get("name", "Produto")
                    campos = product.get("campos", {})
                    campo = campos.get(item.get("campo_id"))
                    campo_name = campo.get("name", "") if campo else "Campo"
                    quantity = item.get("quantity", 1)
                    
                    container_components.append(
                        disnake.ui.TextDisplay(
                            f"-# Produto: `{product_name}`\n"
                            f"-# Campo: `{campo_name}` • Quantidade: `{quantity}`"
                        )
                    )
                    container_components.append(disnake.ui.Separator())
                
                # Informações de pagamento
                payment_info = f"-# Valor: `{price_display}` • Método: `{payment_method_display}`"
                container_components.append(disnake.ui.TextDisplay(payment_info))
                
                # Imagem QR Code
                if qr_attachment_url:
                    container_components.append(disnake.ui.Separator())
                    container_components.append(
                        disnake.ui.MediaGallery(
                            disnake.MediaGalleryItem(media=qr_attachment_url)
                        )
                    )
                
                container_kwargs = {}
                if product_color:
                    container_kwargs["accent_colour"] = product_color
                
                payment_container = disnake.ui.Container(*container_components, **container_kwargs)
                
                # Enviar mensagem de pagamento
                payment_msg = await thread.send(
                    components=[payment_container] + components,
                    files=files if files else None,
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            else:
                # Modo Embed
                embed_color = product_color if product_color else disnake.Color.blue()
                embed = disnake.Embed(
                    title=f"{emoji.cart} Checkout",
                    color=embed_color
                )
                
                # Adicionar produtos
                for item in items:
                    product = products.get(item.get("product_id"))
                    if not product:
                        continue
                    product_name = product.get("name", "Produto")
                    campos = product.get("campos", {})
                    campo = campos.get(item.get("campo_id"))
                    campo_name = campo.get("name", "") if campo else "Campo"
                    quantity = item.get("quantity", 1)
                    
                    embed.add_field(
                        name=f"{emoji.bag} {product_name} (x{quantity})",
                        value=f"Campo: `{campo_name}`",
                        inline=False
                    )
                
                # Informações de pagamento
                embed.add_field(
                    name=f"{emoji.dollar} Pagamento",
                    value=f"Valor: `{price_display}` • Método: `{payment_method_display}`",
                    inline=False
                )
                
                # Adicionar imagem QR Code
                if qr_attachment_url:
                    embed.set_image(url=qr_attachment_url)
                
                embed.timestamp = datetime.utcnow()
                
                payment_msg = await thread.send(
                    embed=embed,
                    components=components,
                    files=files if files else None
                )
            
            # Atualizar carrinho com dados do pagamento
            cart["status"] = "pending"
            cart["message_id"] = payment_msg.id
            cart["total_price"] = final_price
            cart["discount_amount"] = discount_amount
            cart["coupon_code"] = coupon_applied
            cart["coupon_type"] = coupon_type
            cart["is_free_purchase"] = is_free_purchase
            
            # Nova estrutura organizada de payment_data
            cart["payment_data"] = {
                "local": {
                    "copy_code": copy_code,
                    "qr_url": qr_url,
                    "qr_bytes": qr_bytes if qr_bytes else None,
                    "requires_manual_approval": requires_manual_approval
                },
                "provider": {
                    "name": payment_provider,
                    "payment_id": payment_ids.get("payment_id") or payment_ids.get("paymentId"),
                    "correlation_id": payment_ids.get("correlationID") or payment_ids.get("correlation_id"),
                    "charge_id": payment_ids.get("charge_id") or payment_ids.get("id"),
                    "txid": payment_ids.get("txid"),
                    "raw_response": payment_data
                },
                "metadata": {
                    "created_at": int(datetime.utcnow().timestamp()),
                    "payment_method": payment_method,
                    "amount": final_price,
                    "currency": "BRL"
                }
            }
            cart["updated_at"] = int(datetime.utcnow().timestamp())
            
            loja_data["carts"][cart_id] = cart
            db.save_document("loja_data", loja_data)
            
            # Deletar mensagem antiga do carrinho
            try:
                cart_message_id = cart.get("cart_message_id")
                if cart_message_id:
                    cart_msg = await thread.fetch_message(cart_message_id)
                    await cart_msg.delete()
            except:
                pass
            
            # Iniciar monitoramento
            from .checkout import _monitor_payment
            if not is_free_purchase:
                asyncio.create_task(_monitor_payment(cart_id, payment_method, payment_ids, payment_provider, self.bot))
            
            await inter.followup.send(
                f"{emoji.correct} Pagamento criado! Verifique a mensagem acima.",
                ephemeral=True
            )
            return
        
        # Handler para editar quantidade
        if custom_id.startswith("cart_edit_quantity:"):
            parts = custom_id.split(":")
            thread_id = int(parts[1])
            item_idx = int(parts[2])
            cart_id = str(thread_id)
            
            # Carregar carrinho
            loja_data = db.get_document("loja_data")
            cart = loja_data.get("carts", {}).get(cart_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            if cart.get("user_id") != inter.user.id:
                await inter.response.send_message(
                    f"{emoji.wrong} Este não é o seu carrinho!",
                    ephemeral=True
                )
                return
            
            items = cart.get("items", [])
            if item_idx >= len(items):
                await inter.response.send_message(
                    f"{emoji.wrong} Item não encontrado!",
                    ephemeral=True
                )
                return
            
            # Abrir modal para editar quantidade
            item = items[item_idx]
            current_quantity = item.get("quantity", 1)
            
            modal = disnake.ui.Modal(
                title="Editar Quantidade",
                custom_id=f"cart_edit_quantity_modal:{thread_id}:{item_idx}",
                components=[
                    disnake.ui.TextInput(
                        label="Nova Quantidade",
                        placeholder="Digite a nova quantidade",
                        custom_id="new_quantity",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=10,
                        value=str(current_quantity)
                    )
                ]
            )
            
            # Enviar modal com tratamento de erro
            try:
                if not inter.response.is_done():
                    await inter.response.send_modal(modal)
                else:
                    await inter.followup.send(
                        f"{emoji.wrong} Não foi possível abrir o modal. Tente novamente.",
                        ephemeral=True
                    )
            except disnake.errors.NotFound:
                # Interação expirou durante a criação do modal
                if not inter.response.is_done():
                    try:
                        await inter.response.send_message(
                            f"{emoji.wrong} A interação expirou. Por favor, tente novamente.",
                            ephemeral=True
                        )
                    except:
                        pass
                else:
                    try:
                        await inter.followup.send(
                            f"{emoji.wrong} A interação expirou. Por favor, tente novamente.",
                            ephemeral=True
                        )
                    except:
                        pass
            except Exception as e:
                # Outro erro inesperado
                if not inter.response.is_done():
                    try:
                        await inter.response.send_message(
                            f"{emoji.wrong} Ocorreu um erro inesperado: {e}",
                            ephemeral=True
                        )
                    except:
                        pass
                else:
                    try:
                        await inter.followup.send(
                            f"{emoji.wrong} Ocorreu um erro inesperado: {e}",
                            ephemeral=True
                        )
                    except:
                        pass
            return
        
        # Handler para remover item
        if custom_id.startswith("cart_remove_item:"):
            parts = custom_id.split(":")
            thread_id = int(parts[1])
            item_idx = int(parts[2])
            cart_id = str(thread_id)
            
            # Carregar carrinho
            loja_data = db.get_document("loja_data")
            cart = loja_data.get("carts", {}).get(cart_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            if cart.get("user_id") != inter.user.id:
                await inter.response.send_message(
                    f"{emoji.wrong} Este não é o seu carrinho!",
                    ephemeral=True
                )
                return
            
            items = cart.get("items", [])
            if item_idx >= len(items):
                await inter.response.send_message(
                    f"{emoji.wrong} Item não encontrado!",
                    ephemeral=True
                )
                return
            
            # Remover item
            items.pop(item_idx)
            
            if not items:
                # Carrinho vazio - deletar
                await inter.response.send_message(
                    f"{emoji.correct} Último item removido! O carrinho será deletado em breve.",
                    ephemeral=True
                )
                # Gerar e enviar transcript se habilitado (antes de deletar)
                try:
                    from modules.loja.preferences.generate_transcript import generate_cart_transcript, send_cart_transcript_to_channel
                    prefs = db.get_document("loja_preferences") or {}
                    if prefs.get("transcript_enabled", False):
                        transcript_channel_id = prefs.get("transcript_channel_id")
                        if transcript_channel_id:
                            thread = inter.guild.get_thread(thread_id)
                            if thread:
                                transcript_file = await generate_cart_transcript(thread, self.bot, cart)
                                if transcript_file:
                                    await send_cart_transcript_to_channel(self.bot, transcript_file, int(transcript_channel_id), cart)
                except Exception as e:
                    print(f"Erro ao gerar transcript: {e}")
                
                # Deletar thread e carrinho
                try:
                    thread = inter.guild.get_thread(thread_id)
                    if thread:
                        await thread.delete()
                except:
                    pass
                del loja_data["carts"][cart_id]
                db.save_document("loja_data", loja_data)
                return
            
            # Atualizar carrinho
            cart["items"] = items
            cart["total_price"] = sum(item.get("item_total", 0) for item in items)
            cart["updated_at"] = int(datetime.utcnow().timestamp())
            
            loja_data["carts"][cart_id] = cart
            db.save_document("loja_data", loja_data)
            
            # Atualizar mensagem do carrinho
            thread = inter.guild.get_thread(thread_id)
            if thread:
                mode = db.get_document("custom_mode").get("mode", "embed")
                cart_msg_id = cart.get("cart_message_id")
                if cart_msg_id:
                    try:
                        cart_msg = await thread.fetch_message(cart_msg_id)
                        # Reconstruir mensagem
                        new_cart_msg = await _build_cart_message(cart, thread, mode)
                        await cart_msg.delete()
                        cart["cart_message_id"] = new_cart_msg.id
                        loja_data["carts"][cart_id] = cart
                        db.save_document("loja_data", loja_data)
                    except:
                        pass
            
            await inter.response.send_message(
                f"{emoji.correct} Item removido do carrinho com sucesso!",
                ephemeral=True
            )
            return
    
    @commands.Cog.listener("on_modal_submit")
    async def on_edit_quantity_modal(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        
        if not custom_id or not custom_id.startswith("cart_edit_quantity_modal:"):
            return
        
        # Fazer defer imediatamente para evitar timeout
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)
        
        parts = custom_id.split(":")
        thread_id = int(parts[1])
        item_idx = int(parts[2])
        cart_id = str(thread_id)
        
        # Obter nova quantidade
        valores = inter.resolved_values
        new_quantity_str = valores.get("new_quantity", "1")
        
        try:
            new_quantity = int(new_quantity_str)
            if new_quantity < 1:
                new_quantity = 1
        except:
            await inter.followup.send(
                f"{emoji.wrong} Quantidade inválida!",
                ephemeral=True
            )
            return
        
        # Carregar carrinho
        loja_data = db.get_document("loja_data")
        cart = loja_data.get("carts", {}).get(cart_id)
        
        if not cart:
            await inter.followup.send(
                f"{emoji.wrong} Carrinho não encontrado!",
                ephemeral=True
            )
            return
        
        if cart.get("user_id") != inter.user.id:
            await inter.followup.send(
                f"{emoji.wrong} Este não é o seu carrinho!",
                ephemeral=True
            )
            return
        
        items = cart.get("items", [])
        if item_idx >= len(items):
            await inter.followup.send(
                f"{emoji.wrong} Item não encontrado!",
                ephemeral=True
            )
            return
        
        # Atualizar quantidade - validar estoque primeiro
        item = items[item_idx]
        product_id = item.get("product_id")
        campo_id = item.get("campo_id")
        
        # Validar estoque disponível
        from .stock_manager import StockManager
        products = db.get_document("loja_products")
        product = products.get(product_id, {})
        campo = product.get("campos", {}).get(campo_id, {})
        
        # Verificar se é estoque infinito
        infinite_stock = campo.get("infinite_stock", {})
        is_infinite = infinite_stock.get("enabled", False)
        
        if not is_infinite:
            # Verificar estoque disponível
            stock_count = StockManager.get_available_stock(product_id, campo_id)
            
            # Calcular quantidade total já no carrinho (excluindo o item atual)
            total_quantity_in_cart = sum(
                it.get("quantity", 0) for idx, it in enumerate(items) 
                if idx != item_idx and it.get("product_id") == product_id and it.get("campo_id") == campo_id
            )
            
            # Estoque disponível considerando outros itens no carrinho
            available_stock = stock_count - total_quantity_in_cart
            
            if new_quantity > available_stock:
                await inter.followup.send(
                    f"{emoji.wrong} Quantidade inválida! Estoque disponível: `{available_stock}`",
                    ephemeral=True
                )
                return
        
        # Atualizar quantidade
        item["quantity"] = new_quantity
        item["item_total"] = item.get("price_per_unit", 0) * new_quantity
        
        cart["items"] = items
        cart["total_price"] = sum(item.get("item_total", 0) for item in items)
        cart["updated_at"] = int(datetime.utcnow().timestamp())
        
        loja_data["carts"][cart_id] = cart
        db.save_document("loja_data", loja_data)
        
        # Atualizar mensagem do carrinho
        thread = inter.guild.get_thread(thread_id)
        if thread:
            mode = db.get_document("custom_mode").get("mode", "embed")
            cart_msg_id = cart.get("cart_message_id")
            if cart_msg_id:
                try:
                    cart_msg = await thread.fetch_message(cart_msg_id)
                    # Reconstruir mensagem
                    new_cart_msg = await _build_cart_message(cart, thread, mode)
                    await cart_msg.delete()
                    cart["cart_message_id"] = new_cart_msg.id
                    loja_data["carts"][cart_id] = cart
                    db.save_document("loja_data", loja_data)
                except:
                    pass
        
        await inter.followup.send(
            f"{emoji.correct} Quantidade atualizada com sucesso!",
            ephemeral=True
        )
    
    @commands.Cog.listener("on_button_click")
    async def on_coupon_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Handler para aplicar cupom
        if custom_id.startswith("cart_apply_coupon:"):
            thread_id = int(custom_id.split(":")[1])
            cart_id = str(thread_id)
            
            # Criar modal primeiro (operação rápida)
            modal = disnake.ui.Modal(
                title="Aplicar Cupom",
                custom_id=f"cart_coupon_modal:{thread_id}",
                components=[
                    disnake.ui.TextInput(
                        label="Código do Cupom",
                        placeholder="Digite o código do cupom",
                        custom_id="coupon_code",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=30
                    )
                ]
            )
            
            # Tentar abrir modal imediatamente
            try:
                if not inter.response.is_done():
                    await inter.response.send_modal(modal)
                else:
                    # Se já foi respondida, não podemos enviar modal
                    await inter.followup.send(
                        f"{emoji.wrong} Não foi possível abrir o modal. Tente novamente.",
                        ephemeral=True
                    )
            except disnake.errors.NotFound:
                # Interação expirou - tentar enviar mensagem de erro
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            f"{emoji.wrong} A interação expirou. Por favor, tente novamente.",
                            ephemeral=True
                        )
                    else:
                        await inter.followup.send(
                            f"{emoji.wrong} A interação expirou. Por favor, tente novamente.",
                            ephemeral=True
                        )
                except:
                    pass
            except Exception as e:
                # Outro erro - tentar enviar mensagem de erro
                try:
                    if not inter.response.is_done():
                        await inter.response.send_message(
                            f"{emoji.wrong} Erro ao abrir modal: {str(e)}",
                            ephemeral=True
                        )
                    else:
                        await inter.followup.send(
                            f"{emoji.wrong} Erro ao abrir modal: {str(e)}",
                            ephemeral=True
                        )
                except:
                    pass
            return
        
        # Handler para remover cupom
        if custom_id.startswith("cart_remove_coupon:"):
            thread_id = int(custom_id.split(":")[1])
            cart_id = str(thread_id)
            
            # Carregar carrinho
            loja_data = db.get_document("loja_data")
            cart = loja_data.get("carts", {}).get(cart_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            if cart.get("user_id") != inter.user.id:
                await inter.response.send_message(
                    f"{emoji.wrong} Este não é o seu carrinho!",
                    ephemeral=True
                )
                return
            
            # Remover cupom
            cart["coupon_code"] = None
            cart["coupon_type"] = None
            cart["discount_amount"] = 0
            cart["is_free_purchase"] = False
            cart["updated_at"] = int(datetime.utcnow().timestamp())
            
            loja_data["carts"][cart_id] = cart
            db.save_document("loja_data", loja_data)
            
            # Atualizar mensagem do carrinho
            thread = inter.guild.get_thread(thread_id)
            if thread:
                mode = db.get_document("custom_mode").get("mode", "embed")
                cart_msg_id = cart.get("cart_message_id")
                if cart_msg_id:
                    try:
                        cart_msg = await thread.fetch_message(cart_msg_id)
                        # Reconstruir mensagem
                        new_cart_msg = await _build_cart_message(cart, thread, mode)
                        await cart_msg.delete()
                        cart["cart_message_id"] = new_cart_msg.id
                        loja_data["carts"][cart_id] = cart
                        db.save_document("loja_data", loja_data)
                    except:
                        pass
            
            await inter.response.send_message(
                f"{emoji.correct} Cupom removido com sucesso!",
                ephemeral=True
            )
            return
    
    @commands.Cog.listener("on_modal_submit")
    async def on_coupon_modal(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        
        if not custom_id or not custom_id.startswith("cart_coupon_modal:"):
            return
        
        # Fazer defer imediatamente para evitar timeout
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)
        
        thread_id = int(custom_id.split(":")[1])
        cart_id = str(thread_id)
        
        # Obter código do cupom
        valores = inter.resolved_values
        coupon_code = valores.get("coupon_code", "").strip().upper()
        
        if not coupon_code:
            await inter.followup.send(
                f"{emoji.wrong} Código do cupom não pode estar vazio!",
                ephemeral=True
            )
            return
        
        # Carregar carrinho
        loja_data = db.get_document("loja_data")
        cart = loja_data.get("carts", {}).get(cart_id)
        
        if not cart:
            await inter.followup.send(
                f"{emoji.wrong} Carrinho não encontrado!",
                ephemeral=True
            )
            return
        
        if cart.get("user_id") != inter.user.id:
            await inter.followup.send(
                f"{emoji.wrong} Este não é o seu carrinho!",
                ephemeral=True
            )
            return
        
        items = cart.get("items", [])
        if not items:
            await inter.followup.send(
                f"{emoji.wrong} Carrinho vazio!",
                ephemeral=True
            )
            return
        
        # Calcular total do carrinho
        total_price = sum(item.get("item_total", 0) for item in items)
        
        # Validar cupom (tentar com o primeiro produto do carrinho)
        products = db.get_document("loja_products")
        first_item = items[0]
        first_product_id = first_item.get("product_id")
        
        is_valid, error_msg, discount, ctype, coupon_data = CouponValidator.validate_coupon(
            coupon_code,
            first_product_id,
            inter.user.id,
            total_price,
            inter.guild
        )
        
        if not is_valid:
            await inter.followup.send(
                f"{emoji.wrong} Cupom inválido: {error_msg}",
                ephemeral=True
            )
            return
        
        # Aplicar cupom
        cart["coupon_code"] = coupon_code
        cart["coupon_type"] = ctype
        cart["discount_amount"] = discount
        cart["is_free_purchase"] = CouponValidator.is_free_coupon(discount, total_price)
        cart["updated_at"] = int(datetime.utcnow().timestamp())
        
        loja_data["carts"][cart_id] = cart
        db.save_document("loja_data", loja_data)
        
        # Atualizar mensagem do carrinho
        thread = inter.guild.get_thread(thread_id)
        if thread:
            mode = db.get_document("custom_mode").get("mode", "embed")
            cart_msg_id = cart.get("cart_message_id")
            if cart_msg_id:
                try:
                    cart_msg = await thread.fetch_message(cart_msg_id)
                    # Reconstruir mensagem
                    new_cart_msg = await _build_cart_message(cart, thread, mode)
                    await cart_msg.delete()
                    cart["cart_message_id"] = new_cart_msg.id
                    loja_data["carts"][cart_id] = cart
                    db.save_document("loja_data", loja_data)
                except:
                    pass
        
        discount_str = f"R$ {discount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        await inter.followup.send(
            f"{emoji.correct} Cupom `{coupon_code}` aplicado com sucesso! Desconto: `{discount_str}`",
            ephemeral=True
        )
    
    @commands.Cog.listener("on_button_click")
    async def on_balance_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Handler para usar saldo no carrinho
        if custom_id.startswith("cart_use_balance:"):
            thread_id = int(custom_id.split(":")[1])
            cart_id = str(thread_id)
            
            # Verificar se sistema de saldo está habilitado
            saldo_config = db.get_document("loja_saldo_config") or {}
            if not saldo_config.get("enabled", False):
                await inter.response.send_message(
                    f"{emoji.wrong} O sistema de saldo está desabilitado.",
                    ephemeral=True
                )
                return
            
            # Obter saldo do usuário
            from modules.loja.saldo.balance_manager import BalanceManager
            user_balance = BalanceManager.get_user_balance(inter.user.id)
            
            if user_balance <= 0:
                await inter.response.send_message(
                    f"{emoji.wrong} Você não possui saldo disponível.",
                    ephemeral=True
                )
                return
            
            # Carregar carrinho
            loja_data = db.get_document("loja_data")
            cart = loja_data.get("carts", {}).get(cart_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            if cart.get("user_id") != inter.user.id:
                await inter.response.send_message(
                    f"{emoji.wrong} Este não é o seu carrinho!",
                    ephemeral=True
                )
                return
            
            # Calcular total do carrinho
            items = cart.get("items", [])
            total_price = sum(item.get("item_total", 0) for item in items)
            discount_amount = cart.get("discount_amount", 0) or 0
            final_price = max(0, total_price - discount_amount)
            
            # Criar select menu com opções
            await inter.response.send_message(
                f"{emoji.wallet} **Seu saldo:** R$ {user_balance:.2f}\n"
                f"{emoji.cart} **Valor do carrinho:** R$ {final_price:.2f}\n\n"
                f"Selecione como deseja usar o saldo:",
                components=[
                    disnake.ui.ActionRow(
                        disnake.ui.StringSelect(
                            placeholder="Escolha uma opção",
                            custom_id=f"balance_action:{cart_id}",
                            options=[
                                disnake.SelectOption(
                                    label="Pagar totalmente com saldo",
                                    value="pay_full",
                                    description=f"Usar R$ {min(user_balance, final_price):.2f} do saldo",
                                    emoji=emoji.dollar if hasattr(emoji, "dollar") else "💵"
                                ),
                                disnake.SelectOption(
                                    label="Usar saldo parcialmente",
                                    value="pay_partial",
                                    description="Escolher quanto usar do saldo",
                                    emoji=emoji.wallet if hasattr(emoji, "wallet") else "💰"
                                )
                            ]
                        )
                    )
                ],
                ephemeral=True
            )
    
    @commands.Cog.listener("on_dropdown")
    async def on_balance_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Handler para ações de saldo
        if custom_id.startswith("balance_action:"):
            cart_id = custom_id.split(":")[1]
            
            if not inter.values:
                await inter.response.send_message(
                    f"{emoji.wrong} Nenhuma opção selecionada.",
                    ephemeral=True
                )
                return
            
            action = inter.values[0]
            
            # Carregar carrinho
            loja_data = db.get_document("loja_data")
            cart = loja_data.get("carts", {}).get(cart_id)
            
            if not cart:
                await inter.response.send_message(
                    f"{emoji.wrong} Carrinho não encontrado!",
                    ephemeral=True
                )
                return
            
            if cart.get("user_id") != inter.user.id:
                await inter.response.send_message(
                    f"{emoji.wrong} Este não é o seu carrinho!",
                    ephemeral=True
                )
                return
            
            # Obter saldo do usuário
            from modules.loja.saldo.balance_manager import BalanceManager
            user_balance = BalanceManager.get_user_balance(inter.user.id)
            
            # Calcular total do carrinho
            items = cart.get("items", [])
            total_price = sum(item.get("item_total", 0) for item in items)
            discount_amount = cart.get("discount_amount", 0) or 0
            final_price = max(0, total_price - discount_amount)
            
            # Pagar totalmente com saldo
            if action == "pay_full":
                if user_balance < final_price:
                    await inter.response.send_message(
                        f"{emoji.wrong} Saldo insuficiente! Necessário: R$ {final_price:.2f}, Disponível: R$ {user_balance:.2f}",
                        ephemeral=True
                    )
                    return
                
                # Usar saldo
                success, message = BalanceManager.use_balance(
                    inter.user.id,
                    final_price,
                    reference_id=cart_id,
                    description="Pagamento de carrinho com saldo"
                )
                
                if not success:
                    await inter.response.send_message(
                        f"{emoji.wrong} Erro ao usar saldo: {message}",
                        ephemeral=True
                    )
                    return
                
                # Marcar carrinho como pago com saldo
                cart["status"] = "paid_with_balance"
                cart["balance_applied"] = final_price
                cart["payment_method"] = "balance"
                cart["total_price"] = 0
                loja_data["carts"][cart_id] = cart
                db.save_document("loja_data", loja_data)
                
                # Defer para processar a entrega
                await inter.response.defer(ephemeral=True)
                
                # Deletar mensagem do carrinho
                thread_id = cart.get("thread_id")
                thread = inter.guild.get_thread(thread_id) if thread_id else None
                if thread:
                    cart_msg_id = cart.get("cart_message_id")
                    if cart_msg_id:
                        try:
                            cart_msg = await thread.fetch_message(cart_msg_id)
                            await cart_msg.delete()
                        except Exception:
                            pass
                
                # Processar entrega de produtos
                from .delivery import process_automatic_delivery
                
                # Entregar cada item do carrinho
                items = cart.get("items", [])
                products = db.get_document("loja_products")
                
                for item in items:
                    product_id = item.get("product_id")
                    campo_id = item.get("campo_id")
                    quantity = item.get("quantity", 1)
                    
                    product = products.get(product_id, {})
                    product_name = product.get("name", "Produto")
                    campos = product.get("campos", {})
                    campo = campos.get(campo_id, {})
                    campo_name = campo.get("name", "Campo")
                    
                    # Entregar produto
                    await process_automatic_delivery(
                        inter.user,
                        product_id,
                        campo_id,
                        product_name,
                        campo_name,
                        quantity,
                        thread=thread,
                        guild=inter.guild
                    )
                
                # Aplicar cashback ao saldo do usuário
                try:
                    from modules.loja.cashback.manager import CashbackManager
                    if CashbackManager.is_enabled():
                        # Calcular cashback baseado no valor pago com saldo
                        user_roles = []
                        if isinstance(inter.user, disnake.Member):
                            user_roles = [role.id for role in inter.user.roles]
                        
                        cashback_amount = CashbackManager.calculate_cashback(final_price, user_roles)
                        if cashback_amount > 0:
                            success, message = CashbackManager.apply_cashback(
                                inter.user.id,
                                cashback_amount,
                                purchase_ref=cart_id
                            )
                            if success:
                                print(f"[BALANCE_CHECKOUT] Cashback de R$ {cashback_amount:.2f} creditado ao usuário {inter.user.id}")
                except Exception as e:
                    print(f"[BALANCE_CHECKOUT] Erro ao processar cashback: {e}")
                
                # Deletar thread após entrega
                if thread:
                    try:
                        await thread.delete()
                        print(f"[BALANCE_CHECKOUT] Thread {thread_id} deletada após pagamento com saldo")
                    except Exception as e:
                        print(f"[BALANCE_CHECKOUT] Erro ao deletar thread: {e}")
                
                await inter.followup.send(
                    f"{emoji.correct} Pagamento realizado com saldo! Produtos entregues.",
                    ephemeral=True
                )
            
            # Usar saldo parcialmente
            elif action == "pay_partial":
                # Abrir modal para pedir valor
                modal = disnake.ui.Modal(
                    title="Usar Saldo Parcialmente",
                    custom_id=f"partial_balance_modal:{cart_id}",
                    components=[
                        disnake.ui.TextInput(
                            label=f"Quanto usar do saldo? (máx: R$ {min(user_balance, final_price):.2f})",
                            placeholder="Ex: 50.00",
                            custom_id="amount",
                            required=True,
                            max_length=10
                        )
                    ]
                )
                await inter.response.send_modal(modal)
    
    @commands.Cog.listener("on_modal_submit")
    async def on_partial_balance_modal(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        
        # Modal de saldo parcial
        if custom_id.startswith("partial_balance_modal:"):
            cart_id = custom_id.split(":")[1]
            
            try:
                amount = float(inter.text_values["amount"].replace(",", "."))
                
                if amount <= 0:
                    await inter.response.send_message(
                        f"{emoji.wrong} O valor deve ser maior que zero.",
                        ephemeral=True
                    )
                    return
                
                # Carregar carrinho
                loja_data = db.get_document("loja_data")
                cart = loja_data.get("carts", {}).get(cart_id)
                
                if not cart:
                    await inter.response.send_message(
                        f"{emoji.wrong} Carrinho não encontrado!",
                        ephemeral=True
                    )
                    return
                
                # Obter saldo
                from modules.loja.saldo.balance_manager import BalanceManager
                user_balance = BalanceManager.get_user_balance(inter.user.id)
                
                # Calcular total
                items = cart.get("items", [])
                total_price = sum(item.get("item_total", 0) for item in items)
                discount_amount = cart.get("discount_amount", 0) or 0
                final_price = max(0, total_price - discount_amount)
                
                # Validar valores
                if amount > user_balance:
                    await inter.response.send_message(
                        f"{emoji.wrong} Saldo insuficiente! Disponível: R$ {user_balance:.2f}",
                        ephemeral=True
                    )
                    return
                
                if amount > final_price:
                    await inter.response.send_message(
                        f"{emoji.wrong} Valor maior que o total do carrinho (R$ {final_price:.2f})!",
                        ephemeral=True
                    )
                    return
                
                # Aplicar desconto de saldo
                cart["discount_amount"] = (discount_amount or 0) + amount
                cart["balance_to_use"] = amount  # Marcar para usar no checkout
                loja_data["carts"][cart_id] = cart
                db.save_document("loja_data", loja_data)
                
                await inter.response.send_message(
                    f"{emoji.correct} R$ {amount:.2f} do saldo será usado no pagamento!",
                    ephemeral=True
                )
                
                # Atualizar mensagem do carrinho
                thread_id = cart.get("thread_id")
                thread = inter.guild.get_thread(thread_id) if thread_id else None
                if thread:
                    mode = db.get_document("custom_mode").get("mode", "embed")
                    from .checkout import _build_cart_message
                    cart_msg_id = cart.get("cart_message_id")
                    if cart_msg_id:
                        try:
                            cart_msg = await thread.fetch_message(cart_msg_id)
                            new_cart_msg = await _build_cart_message(cart, thread, mode)
                            await cart_msg.delete()
                            cart["cart_message_id"] = new_cart_msg.id
                            loja_data["carts"][cart_id] = cart
                            db.save_document("loja_data", loja_data)
                        except Exception:
                            pass
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.wrong} Valor inválido. Use apenas números.",
                    ephemeral=True
                )
            except Exception as e:
                await inter.response.send_message(
                    f"{emoji.wrong} Erro: {str(e)}",
                    ephemeral=True
                )


def setup(bot: commands.Bot):
    bot.add_cog(CartButtonHandlers(bot))