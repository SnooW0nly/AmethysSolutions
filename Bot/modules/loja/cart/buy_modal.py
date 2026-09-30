import disnake
from disnake.ext import commands
from pathlib import Path
from functions.database import database as db
from functions.emoji import emoji
from typing import Optional, Union, Dict
from .stock_manager import StockManager
import time

from .cart_utils import ensure_emoji, get_available_payment_methods

async def _open_resale_checkout(
    inter: disnake.MessageInteraction,
    product: "ResaleProduct",
    campo_id: str,
    loading_msg=None,
) -> None:
    """
    Abre o checkout para um produto revendido.
    Usa create_checkout com resale_info preenchido.
    """
    from .checkout import create_checkout
    from functions.marketplace import ResaleProduct

    cat = next((c for c in product.categorias if c["id"] == campo_id), None)
    if not cat:
        msg = f"{emoji.wrong} Opção não encontrada."
        if loading_msg:
            await loading_msg.edit(content=msg, components=[])
        else:
            await inter.followup.send(msg, ephemeral=True)
        return

    # Verificar métodos de pagamento — revenda exige pix
    available_methods = get_available_payment_methods()
    if "pix" not in available_methods:
        msg = f"{emoji.wrong} Produtos revendidos exigem **PIX** configurado neste bot."
        if loading_msg:
            await loading_msg.edit(content=msg, components=[])
        else:
            await inter.followup.send(msg, ephemeral=True)
        return

    resale_info = {
        "reseller_user_id": str(inter.author.id),
        "product_name": product.name,
        "bot_id": product.bot_id,
        "product_id": product.product_id,
        "commission_percent": product.resale_commission,
        "owner_amethys_api_key": None,  # será preenchido no cart_continue via get_owner_amethys_config
    }

    if loading_msg:
        try:
            await loading_msg.delete()
        except Exception:
            pass

    await create_checkout(
        inter=inter,
        product_id=product.product_id,
        campo_id=campo_id,
        quantity=1,
        payment_method="pix",
        coupon_code=None,
        resale_info=resale_info,
    )


class BuyProductModal(disnake.ui.Modal):
    """Modal para seleção de campo, quantidade e método de pagamento"""
    
    def _get_available_payment_methods(self) -> dict:
        """Wrapper para manter compatibilidade com o código antigo."""
        return get_available_payment_methods()
    
    def __init__(self, product_id: str, campo_id: Optional[str] = None):
        self.product_id = product_id
        self.campo_id = campo_id
        
        # Carregar informações do produto
        products = db.get_document("loja_products")
        product = products.get(product_id, {})
        product_name = product.get("name", "Produto")
        info = product.get("info") or {}
        delivery_type = info.get("delivery_type", "automatic")
        campos_all = product.get("campos", {})
        
        # Componentes do modal
        components = []
        
        # Se tem múltiplos campos e não foi especificado um, adicionar seletor
        if len(campos_all) > 1 and not campo_id:
            campo_options = []
            for cid, campo in campos_all.items():
                campo_name = campo.get("name", "Campo")
                campo_price = campo.get("price", 0)
                price_str = f"R$ {campo_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                # Obter estoque do sistema centralizado
                stock_count = StockManager.get_available_stock(product_id, cid)
                # Verificar se é estoque infinito (999999 indica infinito)
                is_infinite = stock_count == 999999
                
                # Descrição com preço e estoque
                if is_infinite:
                    description = f"{price_str} | Estoque: Infinito"
                else:
                    description = f"{price_str} | Estoque: {stock_count}"
                
                # Processar emoji do campo usando ensure_emoji para garantir compatibilidade
                campo_emoji_raw = campo.get("emoji")
                campo_emoji = ensure_emoji(campo_emoji_raw)
                
                campo_options.append(
                    disnake.SelectOption(
                        label=campo_name,
                        value=cid,
                        description=description[:100],  # Discord limita a 100 caracteres
                        emoji=campo_emoji
                    )
                )
            
            # Só adicionar o select se houver pelo menos uma opção válida
            if campo_options:
                # Limitar a 25 opções (máximo do Discord)
                campo_options_limited = campo_options[:25]
                components.append(
                    disnake.ui.Label(
                        text="Selecione o Campo",
                        component=disnake.ui.StringSelect(
                            placeholder="Escolha uma opção",
                            custom_id="campo_select",
                            options=campo_options_limited,
                            required=True,
                        ),
                        description="Escolha qual item deseja comprar"
                    )
                )
        
        # Determinar campo selecionado para calcular estoque
        campo_sel_id = campo_id if campo_id and campo_id != "none" else (list(campos_all.keys())[0] if campos_all else None)
        stock_count = StockManager.get_available_stock(product_id, campo_sel_id) if campo_sel_id else 0
        # Verificar se é estoque infinito (999999 indica infinito)
        is_infinite_preview = stock_count == 999999
        max_qty = 99 if delivery_type != "automatic" else (99 if is_infinite_preview else stock_count)
        
        # Campo de quantidade
        components.append(
            disnake.ui.Label(
                text="Quantidade",
                component=disnake.ui.TextInput(
                    placeholder=f"Digite a quantidade (máx: {max_qty if max_qty > 0 else 0})",
                    custom_id="quantity",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    min_length=1,
                    max_length=2,
                    value="1"
                ),
            )
        )
        
        # Verificar métodos de pagamento disponíveis
        available_methods = self._get_available_payment_methods()
        
        # Se não houver métodos disponíveis, não criar o modal
        if not available_methods:
            # Será tratado no listener do botão
            self.no_payment_methods = True
        else:
            self.no_payment_methods = False
        
        # Armazenar método único (se houver apenas um)
        self.single_payment_method = None
        
        # Só adicionar select se houver mais de um método
        if len(available_methods) > 1:
            payment_options = []
            for method_key, method_info in available_methods.items():
                # Garantir que o emoji seja convertido para PartialEmoji quando necessário
                payment_emoji = ensure_emoji(method_info["emoji"])
                payment_options.append(
                    disnake.SelectOption(
                        label=method_info["label"],
                        value=method_key,
                        description=method_info["description"],
                        emoji=payment_emoji
                    )
                )
            
            components.append(
                disnake.ui.Label(
                    text="Método de Pagamento",
                    component=disnake.ui.StringSelect(
                        placeholder="Selecione o método de pagamento",
                        custom_id="payment_method",
                        options=payment_options,
                        required=True,
                    ),
                    description="Escolha como deseja pagar"
                )
            )
        elif len(available_methods) == 1:
            # Se só tem um método, usar automaticamente
            self.single_payment_method = list(available_methods.keys())[0]
        
        # Título do modal
        title = f"Comprar: {product_name}"
        
        super().__init__(
            title=title[:45],  # Discord limita a 45 caracteres
            components=components,
            custom_id=f"buy_product_modal:{product_id}:{campo_id or 'none'}"
        )
    
    async def callback(self, inter: disnake.ModalInteraction):
        """Processar a compra após o modal ser enviado"""
        # Fazer defer imediatamente para não expirar a interação durante verificações async
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)
        
        # Mostrar mensagem de carregamento enquanto verifica
        loading_msg = await inter.followup.send(f"{emoji.loading} Verificando informações...", ephemeral=True)
        
        # Verificações LENTAS (manutenção, horário, verificação OAuth2)
        try:
            # Verificar se está em manutenção
            from modules.loja.preferences.utils import check_maintenance
            is_maintenance, maintenance_msg = check_maintenance(inter.user.id, inter.guild)
            if is_maintenance:
                await loading_msg.edit(content=maintenance_msg or "🔧 Sistema em manutenção. Por favor, tente novamente mais tarde.")
                return
            
            # Verificar horário de funcionamento
            from modules.loja.preferences.utils import check_store_hours
            is_open, hours_msg = check_store_hours()
            if not is_open:
                await loading_msg.edit(content=hours_msg or "⏰ A loja está fora do horário de funcionamento.")
                return
            
            # Verificar se a verificação OAuth2 é obrigatória
            from modules.cloud.verification_check import is_verification_required, send_verification_required_message, is_user_verified
            
            if is_verification_required():
                # Verificar se o usuário está verificado antes de processar a compra
                if isinstance(inter.user, disnake.Member):
                    member = inter.user
                elif inter.guild:
                    member = inter.guild.get_member(inter.user.id)
                else:
                    member = None
                
                if member:
                    verified = await is_user_verified(member)
                    if not verified:
                        # Deletar mensagem de loading e enviar mensagem de verificação
                        try:
                            await loading_msg.delete()
                        except:
                            pass
                        await send_verification_required_message(inter)
                        return
        except Exception as e:
            # Se houver erro na verificação, continuar normalmente (não bloquear)
            print(f"Erro ao verificar no modal de compra: {e}")
        
        # Atualizar loading para "adicionando ao carrinho" em vez de deletar
        try:
            await loading_msg.edit(content="⏳ Adicionando ao carrinho...", components=[])
        except Exception:
            pass

        from .checkout import create_checkout
        
        valores = inter.resolved_values
        
        # Obter campo selecionado (se houver seletor)
        campo_select_value = valores.get("campo_select")
        if campo_select_value:
            # Se é uma lista, pegar o primeiro item
            if isinstance(campo_select_value, (list, tuple)):
                selected_campo_id = campo_select_value[0] if campo_select_value else None
            else:
                selected_campo_id = campo_select_value
        else:
            # Usar o campo_id passado no construtor ou o primeiro campo
            products = db.get_document("loja_products")
            product = products.get(self.product_id, {})
            campos_all = product.get("campos", {})
            selected_campo_id = self.campo_id if self.campo_id and self.campo_id != "none" else (list(campos_all.keys())[0] if campos_all else None)
        
        if not selected_campo_id:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao identificar o campo selecionado!",
                ephemeral=True
            )
            return
        
        # Obter quantidade
        quantity_str = valores.get("quantity", "1")
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError("Quantidade deve ser maior que 0")
            if quantity >= 100:
                raise ValueError("Quantidade deve ter no máximo 2 dígitos")
        except ValueError:
            await inter.followup.send(
                f"{emoji.wrong} Quantidade inválida! Digite um número válido.",
                ephemeral=True
            )
            return
        
        # Validar limite baseado no estoque e tipo de entrega
        products = db.get_document("loja_products")
        product = products.get(self.product_id, {})
        info = product.get("info") or {}
        delivery_type = info.get("delivery_type", "automatic")
        
        # Obter estoque do sistema centralizado
        stock_count = StockManager.get_available_stock(self.product_id, selected_campo_id)
        # Verificar se é estoque infinito (999999 indica infinito)
        is_infinite = stock_count == 999999
        
        # Definir máximo permitido
        if delivery_type != "automatic":
            max_qty = 99
        else:
            max_qty = 99 if is_infinite else int(stock_count)

        # Bloquear compra automática sem estoque (exceto quando infinito)
        if delivery_type == "automatic" and not is_infinite and int(stock_count) <= 0:
            # Criar botão de notificação (apenas emoji, sem label) - garantir compatibilidade com emojis de qualquer servidor
            notify_emoji = ensure_emoji(emoji.warn)
            notify_button = disnake.ui.Button(
                emoji=notify_emoji,
                label="Receber notificação ao repor estoque",
                style=disnake.ButtonStyle.grey,
                custom_id=f"notify_stock:{self.product_id}:{selected_campo_id}"
            )
            
            # Enviar mensagem não-ephemeral para poder editar depois
            await inter.followup.send(
                content=f"{emoji.wrong} Sem estoque disponível para este item.",
                components=[disnake.ui.ActionRow(notify_button)],
                ephemeral=True
            )
            return

        if quantity > max_qty:
            await inter.followup.send(
                f"{emoji.wrong} Quantidade indisponível. Máximo permitido: {max_qty}.",
                ephemeral=True,
            )
            return

        # Obter método de pagamento
        if self.single_payment_method:
            # Se só tem um método, usar automaticamente
            payment_method = self.single_payment_method
        else:
            # Obter do select
            payment_method_value = valores.get("payment_method", "")
            if isinstance(payment_method_value, (list, tuple)):
                payment_method = payment_method_value[0] if payment_method_value else None
            else:
                payment_method = payment_method_value or None
            
            if not payment_method:
                await inter.followup.send(
                    f"{emoji.wrong} Selecione um método de pagamento!",
                    ephemeral=True
                )
                return
        
        # Criar checkout sem cupom (cupom será aplicado no carrinho)
        await create_checkout(
            inter=inter,
            product_id=self.product_id,
            campo_id=selected_campo_id,
            quantity=quantity,
            payment_method=payment_method,
            coupon_code=None,  # Cupom será aplicado no carrinho
            loading_msg=loading_msg,  # Reutilizar loading para evitar criar nova mensagem
        )


async def _validate_before_cart_creation(
    inter: disnake.MessageInteraction,
    product_id: str,
    campo_id: str,
) -> tuple[bool, Optional[str], Optional[Dict]]:
    """
    Valida TUDO antes de criar o carrinho.
    Retorna: (success, error_message, cart_data_dict)
    Se success=True, cart_data_dict contém todos os dados necessários para criar o carrinho.
    """
    # 1. Verificar manutenção
    try:
        from modules.loja.preferences.utils import check_maintenance
        is_maintenance, maintenance_msg = check_maintenance(inter.user.id, inter.guild)
        if is_maintenance:
            return False, maintenance_msg or "🔧 Sistema em manutenção. Por favor, tente novamente mais tarde.", None
    except Exception as e:
        print(f"Erro ao verificar manutenção: {e}")
        # Continuar mesmo com erro na verificação
    
    # 2. Verificar horário de funcionamento
    try:
        from modules.loja.preferences.utils import check_store_hours
        is_open, hours_msg = check_store_hours()
        if not is_open:
            return False, hours_msg or "⏰ A loja está fora do horário de funcionamento.", None
    except Exception as e:
        print(f"Erro ao verificar horário: {e}")
        # Continuar mesmo com erro na verificação
    
    # 3. Verificar verificação OAuth2
    try:
        from modules.cloud.verification_check import is_verification_required, is_user_verified
        if is_verification_required():
            if isinstance(inter.user, disnake.Member):
                member = inter.user
            elif inter.guild:
                member = inter.guild.get_member(inter.user.id)
            else:
                member = None
            
            if member:
                verified = await is_user_verified(member)
                if not verified:
                    return False, None, None  # Será tratado pelo send_verification_required_message
    except Exception as e:
        print(f"Erro ao verificar OAuth2: {e}")
        # Continuar mesmo com erro na verificação
    
    # 4. Carregar e validar produto
    products = db.get_document("loja_products")
    product = products.get(product_id, {})
    if not product:
        return False, f"{emoji.wrong} Produto não encontrado.", None
    
    campos = product.get("campos", {})
    campo = campos.get(campo_id)
    if not campo:
        return False, f"{emoji.wrong} Campo não encontrado para este produto.", None
    
    info = product.get("info") or {}
    delivery_type = info.get("delivery_type", "automatic")
    price = campo.get("price", 0)
    
    # 5. Validar estoque
    stock_count = StockManager.get_available_stock(product_id, campo_id)
    is_infinite = stock_count == 999999
    
    if delivery_type == "automatic" and not is_infinite and int(stock_count) <= 0:
        # Retornar flag especial para mostrar botão de notificação
        return False, "NO_STOCK", {"product_id": product_id, "campo_id": campo_id}
    
    # 6. Verificar métodos de pagamento
    available_methods = get_available_payment_methods()
    if not available_methods:
        return False, f"{emoji.wrong} Nenhum método de pagamento está disponível no momento. Entre em contato com um administrador.", None
    
    # 7. Escolher método padrão
    if "pix" in available_methods:
        payment_method = "pix"
    else:
        payment_method = next(iter(available_methods.keys()))
    
    # 8. Preparar dados do carrinho
    quantity = 1  # Quantidade padrão
    cart_data = {
        "product_id": product_id,
        "campo_id": campo_id,
        "quantity": quantity,
        "price": price,
        "payment_method": payment_method,
        "delivery_type": delivery_type,
        "product": product,
        "campo": campo,
    }
    
    return True, None, cart_data


async def _add_product_to_cart_from_interaction(
    inter: disnake.MessageInteraction,
    product_id: str,
    campo_id: str,
    loading_msg: Optional[disnake.Message] = None,
) -> None:
    """Adiciona um produto (campo específico) ao carrinho com quantidade 1."""
    from .checkout import create_checkout
    
    # VALIDAR TUDO ANTES DE CRIAR O CARRINHO
    success, error_msg, cart_data = await _validate_before_cart_creation(inter, product_id, campo_id)
    
    if not success:
        # Tratar verificação OAuth2 separadamente
        if error_msg is None:
            # Usar a mesma mensagem e botão de verificação que os tickets usam
            from modules.cloud.verification_check import get_verification_message_and_view, send_verification_required_message
            
            message_text, view = get_verification_message_and_view(inter)
            
            # Editar mensagem de loading se existir
            if loading_msg:
                try:
                    if message_text and view:
                        await loading_msg.edit(
                            content=message_text,
                            view=view
                        )
                    else:
                        await loading_msg.edit(
                            content="Esse servidor requer que você seja verificado para usar algumas funcionalidades."
                        )
                except:
                    pass
            else:
                try:
                    await send_verification_required_message(inter)
                except:
                    # Fallback se a função falhar
                    fallback_msg = "Esse servidor requer que você seja verificado para usar algumas funcionalidades."
                    if inter.response.is_done():
                        await inter.followup.send(
                            fallback_msg,
                            ephemeral=True,
                            view=view if view else None
                        )
                    else:
                        await inter.response.send_message(
                            fallback_msg,
                            ephemeral=True,
                            view=view if view else None
                        )
            return
        
        # Tratar estoque sem disponibilidade
        if error_msg == "NO_STOCK":
            notify_emoji = ensure_emoji(emoji.warn)
            notify_button = disnake.ui.Button(
                emoji=notify_emoji,
                label="Receber notificação ao repor estoque",
                style=disnake.ButtonStyle.grey,
                custom_id=f"notify_stock:{cart_data['product_id']}:{cart_data['campo_id']}"
            )
            
            # Editar mensagem de loading se existir
            if loading_msg:
                try:
                    await loading_msg.edit(
                        content=f"{emoji.wrong} Sem estoque disponível para este item.",
                        components=[disnake.ui.ActionRow(notify_button)]
                    )
                except:
                    # Se não conseguir editar, enviar nova mensagem
                    await inter.followup.send(
                        content=f"{emoji.wrong} Sem estoque disponível para este item.",
                        components=[disnake.ui.ActionRow(notify_button)],
                        ephemeral=True
                    )
            else:
                if inter.response.is_done():
                    await inter.followup.send(
                        content=f"{emoji.wrong} Sem estoque disponível para este item.",
                        components=[disnake.ui.ActionRow(notify_button)],
                        ephemeral=True
                    )
                else:
                    await inter.response.send_message(
                        content=f"{emoji.wrong} Sem estoque disponível para este item.",
                        components=[disnake.ui.ActionRow(notify_button)],
                        ephemeral=True
                    )
            return
        
        # Outros erros - editar mensagem de loading se existir
        if loading_msg:
            try:
                await loading_msg.edit(content=error_msg)
            except:
                if inter.response.is_done():
                    await inter.followup.send(error_msg, ephemeral=True)
                else:
                    await inter.response.send_message(error_msg, ephemeral=True)
        else:
            if inter.response.is_done():
                await inter.followup.send(error_msg, ephemeral=True)
            else:
                await inter.response.send_message(error_msg, ephemeral=True)
        return
    
    # Tudo validado! Criar carrinho com dados já preparados
    # Passar loading_msg para create_checkout editar ao invés de criar nova mensagem
    await create_checkout(
        inter=inter,
        product_id=cart_data["product_id"],
        campo_id=cart_data["campo_id"],
        quantity=cart_data["quantity"],
        payment_method=cart_data["payment_method"],
        coupon_code=None,
        loading_msg=loading_msg,  # Passar mensagem de loading para editar
    )


class BuyProductButton(commands.Cog):
    """Listener para botões de compra e notificações de estoque"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener("on_button_click")
    async def on_buy_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if not custom_id or not any(custom_id.startswith(p) for p in (
            "disable_stock_notification:", "notify_stock:", "buy_resale:", "buy_product:"
        )):
            return

        if inter.response.is_done():
            return

        # Handler para desativar notificação de estoque
        if custom_id.startswith("disable_stock_notification:"):
            parts = custom_id.split(":")
            product_id = parts[1] if len(parts) >= 2 else None
            campo_id = parts[2] if len(parts) >= 3 else None
            
            if not product_id or not campo_id:
                await inter.response.send_message(f"{emoji.wrong} Erro ao processar desativação.", ephemeral=True)
                return
            
            # Defer antes das operações de banco para evitar timeout
            if not inter.response.is_done():
                await inter.response.defer(ephemeral=True)
            
            notifications_doc = db.get_document("loja_stock_notifications") or {}
            notifications = notifications_doc.get("notifications", {})
            
            # Criar chave única: user_id:product_id:campo_id
            user_id_str = str(inter.user.id)
            notification_key = f"{user_id_str}:{product_id}:{campo_id}"
            
            # Remover notificação se existir
            if notification_key in notifications:
                del notifications[notification_key]
                notifications_doc["notifications"] = notifications
                db.save_document("loja_stock_notifications", notifications_doc)
                message_text = f"{emoji.correct} Notificação de estoque desativada com sucesso!"
            else:
                message_text = f"{emoji.wrong} Você não possui notificação ativa para este produto."
            
            await inter.followup.send(message_text, ephemeral=True)
            return
        
        # Handler para notificação de estoque
        if custom_id.startswith("notify_stock:"):
            parts = custom_id.split(":")
            product_id = parts[1] if len(parts) >= 2 else None
            campo_id = parts[2] if len(parts) >= 3 else None
            
            if not product_id or not campo_id:
                await inter.response.send_message(f"{emoji.wrong} Erro ao processar notificação.", ephemeral=True)
                return
            
            # Defer antes das operações de banco para evitar timeout
            if not inter.response.is_done():
                await inter.response.defer(ephemeral=True)
            
            notifications_doc = db.get_document("loja_stock_notifications") or {}
            notifications = notifications_doc.get("notifications", {})
            
            # Criar chave única: user_id:product_id:campo_id
            user_id_str = str(inter.user.id)
            notification_key = f"{user_id_str}:{product_id}:{campo_id}"
            
            # Verificar se já existe notificação
            if notification_key in notifications:
                # Remover notificação
                del notifications[notification_key]
                notifications_doc["notifications"] = notifications
                db.save_document("loja_stock_notifications", notifications_doc)
                message_text = f"{emoji.wrong} Notificação de estoque cancelada. Você não será notificado quando o estoque for reposto."
            else:
                # Adicionar notificação
                notifications[notification_key] = {
                    "user_id": user_id_str,
                    "product_id": product_id,
                    "campo_id": campo_id,
                    "created_at": int(disnake.utils.utcnow().timestamp()),
                    "notified": False
                }
                notifications_doc["notifications"] = notifications
                db.save_document("loja_stock_notifications", notifications_doc)
                message_text = f"{emoji.correct} Você será notificado quando o estoque deste produto estiver disponível!"
            
            # Enviar mensagem de confirmação ephemeral
            await inter.followup.send(
                message_text,
                ephemeral=True
            )
            return
        
        # ── Compra de produto revendido ──────────────────────────────────────────
        # Formato: "buy_resale:{bot_id}::{product_id}"
        if custom_id.startswith("buy_resale:"):
            select_value = custom_id[len("buy_resale:"):]  # "{bot_id}::{product_id}"

            if not inter.response.is_done():
                await inter.response.defer(ephemeral=True)

            _resale_loading = None
            try:
                _resale_loading = await inter.followup.send(
                    "⏳ Carregando produto, aguarde...", ephemeral=True
                )
            except Exception:
                pass

            from functions.marketplace import fetch_resale_products
            products = fetch_resale_products(force_refresh=False)
            product = next((p for p in products if p.select_value == select_value), None)

            if not product:
                await inter.followup.send(
                    f"{emoji.wrong} Produto de revenda não encontrado. Tente novamente.",
                    ephemeral=True,
                )
                return

            # Se só tem um campo, abrir carrinho direto
            if len(product.categorias) == 1:
                cat = product.categorias[0]
                await _open_resale_checkout(inter, product, cat["id"], None)
                return

            # Múltiplos campos — mostrar select
            options = [
                disnake.SelectOption(
                    label=cat["name"][:100],
                    value=cat["id"],
                    description=f"R$ {cat['resale_price']:.2f}"[:100],
                )
                for cat in product.categorias
            ]
            select = disnake.ui.StringSelect(
                placeholder="Selecione uma opção para continuar...",
                custom_id=f"buy_resale_select:{select_value}",
                options=options[:25],
            )
            await inter.followup.send(
                content="Selecione uma opção:",
                components=[disnake.ui.ActionRow(select)],
                ephemeral=True,
            )
            return

        # Formato: "buy_product:<product_id>" ou "buy_product:<product_id>:<campo_id>"
        if custom_id.startswith("buy_product:"):
            parts = custom_id.split(":", 2)
            product_id = parts[1] if len(parts) >= 2 else None
            campo_id = parts[2] if len(parts) >= 3 else None
            
            if not product_id:
                return
            
            # 1) Enviar mensagem de loading imediata
            loading_msg = None
            if not inter.response.is_done():
                # Primeiro responde, depois tenta recuperar a mensagem original
                await inter.response.send_message(
                    f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Carregando opções...",
                    ephemeral=True
                )
                try:
                    loading_msg = await inter.original_message()
                except Exception:
                    loading_msg = None
            else:
                try:
                    loading_msg = await inter.followup.send(
                        f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Carregando opções...",
                        ephemeral=True
                    )
                except Exception:
                    loading_msg = None
            
            # 2) Carregar produto e campos
            products = db.get_document("loja_products")
            product = products.get(product_id, {})
            campos = product.get("campos", {})
            
            if not product:
                if loading_msg:
                    await loading_msg.edit(
                        content=f"{emoji.wrong} Produto não encontrado.",
                        components=[]
                    )
                else:
                    await inter.followup.send(
                        f"{emoji.wrong} Produto não encontrado.",
                        ephemeral=True
                    )
                return
            
            if not campos:
                if loading_msg:
                    await loading_msg.edit(
                        content=f"{emoji.wrong} Não há campos configurados para este produto.",
                        components=[]
                    )
                else:
                    await inter.followup.send(
                        f"{emoji.wrong} Não há campos configurados para este produto.",
                        ephemeral=True
                    )
                return
            
            # Se já veio um campo específico no botão, adicionar direto ao carrinho
            if campo_id:
                # Atualizar loading para "Adicionando ao carrinho..."
                if loading_msg:
                    try:
                        await loading_msg.edit(
                            content=f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Adicionando ao carrinho...",
                            components=[]
                        )
                    except:
                        pass
                await _add_product_to_cart_from_interaction(inter, product_id, campo_id, loading_msg)
                return
            
            # Se só tiver um campo, usar diretamente (sem select)
            if len(campos) == 1:
                only_campo_id = next(iter(campos.keys()))
                # Atualizar loading para "Adicionando ao carrinho..."
                if loading_msg:
                    try:
                        await loading_msg.edit(
                            content=f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Adicionando ao carrinho...",
                            components=[]
                        )
                    except:
                        pass
                await _add_product_to_cart_from_interaction(inter, product_id, only_campo_id, loading_msg)
                return
            
            # 3) Se tiver múltiplos campos, transformar a mensagem de loading em select efêmero
            options = []
            for cid, campo in campos.items():
                campo_name = campo.get("name", "Campo")
                campo_price = campo.get("price", 0)
                price_str = f"R$ {campo_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                stock_count = StockManager.get_available_stock(product_id, cid)
                is_infinite = stock_count == 999999
                if is_infinite:
                    description = f"{price_str} | Estoque: Infinito"
                else:
                    description = f"{price_str} | Estoque: {stock_count}"
                
                campo_emoji_raw = campo.get("emoji")
                campo_emoji = ensure_emoji(campo_emoji_raw)
                
                options.append(
                    disnake.SelectOption(
                        label=campo_name,
                        value=cid,
                        description=description[:100],
                        emoji=campo_emoji
                    )
                )
            
            select = disnake.ui.StringSelect(
                placeholder="Selecione uma opção para continuar...",
                custom_id=f"buy_product_select_field:{product_id}",
                options=options[:25],
            )
            
            # 3) Atualizar a mensagem de loading para mostrar o select; se não houver mensagem, enviar nova
            if loading_msg:
                await loading_msg.edit(
                    content=None,
                    components=[disnake.ui.ActionRow(select)]
                )
            else:
                await inter.followup.send(
                    content=None,
                    components=[disnake.ui.ActionRow(select)],
                    ephemeral=True
                )
            return
    
    @commands.Cog.listener("on_dropdown")
    async def on_buy_dropdown(self, inter: disnake.MessageInteraction):
        """Handler para selects relacionados à compra (campos de produto)."""
        custom_id = inter.component.custom_id or ""
        
        # ── Select de campo de produto revendido ─────────────────────────────────
        if custom_id.startswith("buy_resale_select:"):
            select_value = custom_id[len("buy_resale_select:"):]
            campo_id = inter.values[0] if inter.values else None

            if not campo_id:
                if not inter.response.is_done():
                    await inter.response.send_message(f"{emoji.wrong} Campo inválido.", ephemeral=True)
                else:
                    await inter.followup.send(f"{emoji.wrong} Campo inválido.", ephemeral=True)
                return

            if not inter.response.is_done():
                await inter.response.defer(ephemeral=True)

            from functions.marketplace import fetch_resale_products
            products = fetch_resale_products(force_refresh=False)
            product = next((p for p in products if p.select_value == select_value), None)

            if not product:
                await inter.followup.send(f"{emoji.wrong} Produto de revenda não encontrado.", ephemeral=True)
                return

            await _open_resale_checkout(inter, product, campo_id, None)
            return

        if custom_id.startswith("buy_product_select_field:"):
            parts = custom_id.split(":", 1)
            product_id = parts[1] if len(parts) == 2 else None
            if not product_id:
                return
            
            campo_id = inter.values[0] if inter.values else None
            if not campo_id:
                # Responder imediatamente se campo inválido
                if not inter.response.is_done():
                    await inter.response.send_message(
                        f"{emoji.wrong} Campo inválido selecionado.",
                        ephemeral=True,
                    )
                else:
                    await inter.followup.send(
                        f"{emoji.wrong} Campo inválido selecionado.",
                        ephemeral=True,
                    )
                return
            
            # 1. Guardar referência da mensagem do select antes de responder
            select_message = inter.message
            
            # 2. Responder imediatamente com mensagem de loading
            loading_msg = None
            if not inter.response.is_done():
                # Primeiro, tentar editar a mensagem do select para remover componentes
                try:
                    await inter.response.edit_message(
                        content=f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Adicionando ao carrinho...",
                        components=[]
                    )
                    # Se editou com sucesso, usar essa mensagem como loading_msg
                    try:
                        loading_msg = await inter.original_message()
                    except:
                        pass
                except:
                    # Se não conseguir editar, enviar nova mensagem efêmera
                    try:
                        await inter.response.send_message(
                            f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Adicionando ao carrinho...",
                            ephemeral=True
                        )
                        # Tentar deletar a mensagem do select após enviar nova mensagem
                        if select_message:
                            try:
                                await select_message.delete()
                            except:
                                pass
                    except:
                        # Se falhar, fazer defer e enviar followup
                        await inter.response.defer(ephemeral=True)
                        loading_msg = await inter.followup.send(
                            f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Adicionando ao carrinho...",
                            ephemeral=True
                        )
                        # Tentar deletar a mensagem do select após enviar followup
                        if select_message:
                            try:
                                await select_message.delete()
                            except:
                                pass
            else:
                # Se já foi respondida, enviar followup
                loading_msg = await inter.followup.send(
                    f"{emoji.loading if hasattr(emoji, 'loading') else '⏳'} Adicionando ao carrinho...",
                    ephemeral=True
                )
                # Tentar deletar a mensagem do select após enviar followup
                if select_message:
                    try:
                        await select_message.delete()
                    except:
                        pass
            
            # 3. Adicionar item selecionado ao carrinho
            # A função _add_product_to_cart_from_interaction vai editar a mensagem de loading
            # ou criar uma nova mensagem com o resultado
            await _add_product_to_cart_from_interaction(inter, product_id, campo_id, loading_msg)
            return


def setup(bot: commands.Bot):
    bot.add_cog(BuyProductButton(bot))