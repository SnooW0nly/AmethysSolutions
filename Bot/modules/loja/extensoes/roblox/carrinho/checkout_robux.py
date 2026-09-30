import disnake
import asyncio
import base64
import io
from disnake.ext import commands
from typing import Optional, Dict, Any

from functions.database import database as db
from functions.emoji import emoji
from functions.email_utils import send_sale_email_robux
from functions.payments import (
    create_mp_payment_from_settings,
    create_efi_payment_from_settings,
    create_manual_pix_payment,
    create_misticpay_payment_from_settings,
    check_mp_payment_from_settings,
    check_efi_payment_from_settings,
    check_pushinpay_payment_from_settings,
    check_misticpay_payment_from_settings,
    check_manual_pix_payment,
    approve_manual_pix_payment,
)
from .config import get_roblox_config
from .roblox_orders import get_order, update_order, get_order_by_thread
from .ticket_manager import _build_payment_approved_message


def _get_active_payment_provider() -> Optional[str]:
    from pathlib import Path as _Path
    pagamentos_doc = db.get_document("pagamentos") or {}
    payment_configs = db.get_document("payment_configs") or {}
    priority = [
        "amethys_wallet", "mercado_pago", "efibank", "pushinpay", "misticpay", "pix_manual"
    ]
    for provider in priority:
        cfg = payment_configs.get(provider, {})
        if not isinstance(cfg, dict):
            cfg = {}
        is_enabled = bool(cfg.get("enabled", False)) or bool(pagamentos_doc.get(provider, False))
        if not is_enabled:
            continue
        if provider == "amethys_wallet":
            if cfg.get("api_key") or cfg.get("token") or cfg.get("access_token"):
                return provider
        elif provider == "mercado_pago":
            if cfg.get("access_token"):
                return provider
        elif provider == "efibank":
            cert_path = cfg.get("cert_file")
            cert_ok = bool(cert_path) and _Path(cert_path).exists()
            if cfg.get("client_id") and cfg.get("client_secret") and cfg.get("pix_key") and cert_ok:
                return provider
        elif provider == "pushinpay":
            if cfg.get("token_pushinpay"):
                return provider
        elif provider == "misticpay":
            if cfg.get("client_id") and cfg.get("client_secret"):
                return provider
        elif provider == "pix_manual":
            if cfg.get("pix_key") and cfg.get("pix_key_type"):
                return provider
    return None


def _get_cart_timeout_seconds() -> int:
    """
    Lê o tempo de expiração do carrinho em minutos de loja_preferences.
    Fallback: 30 minutos se não configurado.
    """
    prefs = db.get_document("loja_preferences") or {}
    minutes = prefs.get("cart_duration_minutes", 30)
    try:
        minutes = int(minutes)
    except Exception:
        minutes = 30
    return max(1, minutes) * 60


def _apply_amethys_fee_if_needed(base_price: float, provider: str) -> tuple:
    """
    Replica a lógica do cart_handlers: se Amethys Wallet está ativo e
    customer_pays_fee=True, busca o % do plano via DB e soma R$ 0,50 fixo da Mistic.
    Retorna (final_price, fee_added).
    ATENÇÃO: essa função é síncrona — a chamada assíncrona à API do plano fica em
    _fetch_amethys_plan_fee(). Aqui apenas aplica se o fee já foi resolvido.
    """
    if provider != "amethys_wallet" or base_price <= 0:
        return base_price, 0.0

    payment_configs_doc = db.get_document("payment_configs") or {}
    pagamentos_doc = db.get_document("pagamentos") or {}
    amethys_cfg = payment_configs_doc.get("amethys_wallet") or {}
    amethys_enabled = bool(amethys_cfg.get("enabled", False)) or bool(pagamentos_doc.get("amethys_wallet", False))
    customer_pays_fee = amethys_cfg.get("customer_pays_fee", False)

    if not amethys_enabled or not customer_pays_fee:
        return base_price, 0.0

    return None, None  # sinaliza que precisa buscar % via API


async def _resolve_amethys_fee(base_price: float) -> float:
    """
    Busca o transactionFeePercent do plano atual via API Amethys e
    calcula o valor final com taxa repassada ao cliente, igual ao cart_handlers:
      taxa = (base_price * fee_percent / 100) + R$ 0,50 fixo Mistic
    Retorna o final_price já com taxa incluída.
    """
    try:
        from functions.payments.amethys_wallet import _request, _get_api_key
        api_key = _get_api_key()
        plan_result = await asyncio.wait_for(
            _request("GET", "api/v1/user/my-plan", api_key=api_key),
            timeout=10,
        )
        plan_data = plan_result.get("data", {}).get("currentPlan", {})
        fee_percent = float(plan_data.get("transactionFeePercent") or 0)

        mistic_fixed = 0.50  # R$ 0,50 fixo da Mistic — imutável
        platform_fee = round(base_price * fee_percent / 100, 2)
        fee_added = round(platform_fee + mistic_fixed, 2)
        final_price = round(base_price + fee_added, 2)

        print(
            f"[RobloxCheckout] Taxa Amethys repassada ao cliente: "
            f"R$ {fee_added:.2f} ({fee_percent}% = R$ {platform_fee:.2f} + Mistic R$ {mistic_fixed:.2f}) "
            f"| Base: R$ {base_price:.2f} → Final: R$ {final_price:.2f}"
        )
        return final_price
    except Exception as e:
        print(f"[RobloxCheckout] Erro ao buscar taxa do plano Amethys: {e} — usando valor sem taxa")
        return base_price


async def _create_payment(order: dict, provider: str):
    """Retorna tupla (payment_result, charged_price). payment_result é None em caso de falha."""
    import traceback as _traceback
    base_price = order.get("total_price", 0)
    order_id = order.get("order_id", "?")
    description = f"Robux - Pedido #{order_id}"

    # ── Aplicar taxa do gateway ao cliente (igual ao cart_handlers) ──────────
    final_price = base_price
    if provider == "amethys_wallet":
        sentinel, _ = _apply_amethys_fee_if_needed(base_price, provider)
        if sentinel is None:
            # customer_pays_fee=True → buscar % do plano via API
            final_price = await _resolve_amethys_fee(base_price)
    # ─────────────────────────────────────────────────────────────────────────

    _MAX_RETRIES = 3
    _TIMEOUT = 15

    async def _attempt_amethys():
        from functions.payments.amethys_wallet import create_amethys_payment_from_settings
        return await asyncio.wait_for(
            create_amethys_payment_from_settings(value=final_price, description=description),
            timeout=_TIMEOUT,
        )

    try:
        if provider == "amethys_wallet":
            last_exc = None
            for attempt in range(1, _MAX_RETRIES + 1):
                try:
                    result = await _attempt_amethys()
                    return result, final_price
                except (asyncio.TimeoutError, asyncio.CancelledError) as e:
                    last_exc = e
                    print(f"[RobloxCheckout] Timeout na tentativa {attempt}/{_MAX_RETRIES} (amethys_wallet): {e}")
                    if attempt < _MAX_RETRIES:
                        await asyncio.sleep(2 * attempt)
                except Exception as e:
                    last_exc = e
                    print(f"[RobloxCheckout] Erro na tentativa {attempt}/{_MAX_RETRIES} (amethys_wallet): {e}")
                    _traceback.print_exc()
                    if attempt < _MAX_RETRIES:
                        await asyncio.sleep(2 * attempt)
            print(f"[RobloxCheckout] Todas as {_MAX_RETRIES} tentativas falharam (amethys_wallet). Último erro: {last_exc}")
            return None, final_price
        elif provider == "mercado_pago":
            return await create_mp_payment_from_settings(final_price), final_price
        elif provider == "efibank":
            return await create_efi_payment_from_settings(price=final_price), final_price
        elif provider == "pushinpay":
            from functions.payments import create_pushinpay_payment_from_settings
            return await create_pushinpay_payment_from_settings(int(round(final_price * 100))), final_price
        elif provider == "misticpay":
            return await create_misticpay_payment_from_settings(
                amount=final_price,
                payer_name="Cliente",
                payer_document="00000000000",
                description=description,
            ), final_price
        elif provider == "pix_manual":
            return await create_manual_pix_payment(final_price, description=description), final_price
    except Exception as e:
        print(f"[RobloxCheckout] Erro ao criar pagamento ({provider}): {e}")
        _traceback.print_exc()
    return None, final_price


def _extract_copy_code(data: dict) -> Optional[str]:
    keys = ["copy_paste", "pix_copia_cola", "emv", "code", "qr_code_text", "qrcode_text", "pixCopyPaste", "qrCode"]
    for k in keys:
        if data.get(k):
            return str(data[k])
    raw = data.get("raw", {})
    if isinstance(raw, dict):
        for k in keys:
            if raw.get(k):
                return str(raw[k])
    return None


def _extract_qr_bytes(data: dict) -> Optional[bytes]:
    qr_bytes = data.get("qr_code_bytes")
    if isinstance(qr_bytes, bytes):
        return qr_bytes
    b64 = data.get("qr_code_base64") or data.get("qrcode_base64")
    if isinstance(b64, str):
        try:
            if "," in b64:
                b64 = b64.split(",", 1)[1]
            return base64.b64decode(b64)
        except Exception:
            pass
    raw = data.get("raw", {})
    if isinstance(raw, dict):
        b64 = raw.get("qr_code_base64") or raw.get("point_of_interaction", {}).get("transaction_data", {}).get("qr_code_base64")
        if isinstance(b64, str):
            try:
                return base64.b64decode(b64)
            except Exception:
                pass
    return None


def _extract_payment_id(data: dict) -> Optional[str]:
    for k in ["payment_id", "paymentId", "id", "correlationID", "txid"]:
        val = data.get(k)
        if val:
            return str(val)
    raw = data.get("raw", {})
    if isinstance(raw, dict):
        for k in ["id", "paymentId", "correlationID", "txid"]:
            val = raw.get(k)
            if val:
                return str(val)
    return None


async def _check_payment_status(provider: str, payment_data: dict) -> bool:
    try:
        raw_data = payment_data.get("raw", {}) or {}
        if provider == "amethys_wallet":
            pid = payment_data.get("payment_id") or _extract_payment_id(raw_data) or _extract_payment_id(payment_data)
            if pid:
                from functions.payments.amethys_wallet import check_amethys_payment_from_settings
                result = await check_amethys_payment_from_settings(pid)
                return result.get("status") == "approved"
        elif provider == "mercado_pago":
            pid = payment_data.get("payment_id") or _extract_payment_id(raw_data) or _extract_payment_id(payment_data)
            if pid:
                result = await check_mp_payment_from_settings(pid)
                return result.get("status") == "approved"
        elif provider == "efibank":
            txid = payment_data.get("txid") or raw_data.get("txid")
            if txid:
                result = await check_efi_payment_from_settings(txid)
                return result.get("status") in ("CONCLUIDA", "approved")
        elif provider == "pushinpay":
            pid = payment_data.get("payment_id") or _extract_payment_id(raw_data) or _extract_payment_id(payment_data)
            if pid:
                result = await check_pushinpay_payment_from_settings(pid)
                return result.get("status") == "approved"
        elif provider == "misticpay":
            pid = payment_data.get("payment_id") or _extract_payment_id(raw_data) or _extract_payment_id(payment_data)
            if pid:
                result = await check_misticpay_payment_from_settings(pid)
                return result.get("status") == "approved"
        elif provider == "pix_manual":
            pid = payment_data.get("payment_id") or _extract_payment_id(payment_data)
            if pid:
                result = await check_manual_pix_payment(pid)
                return result.get("status") == "approved"
    except Exception as e:
        print(f"[RobloxCheckout] Erro ao verificar pagamento: {e}")
    return False


async def _try_send_transcript(bot, channel: disnake.TextChannel, order: dict):
    """
    Gera e envia o transcript do ticket para o canal de log configurado,
    se transcripts estiverem habilitados nas preferências da loja.
    """
    try:
        prefs = db.get_document("loja_preferences") or {}
        if not prefs.get("transcript_enabled", False):
            return
        transcript_channel_id = prefs.get("transcript_channel_id")
        if not transcript_channel_id:
            return

        from .generate_transcript import generate_cart_transcript, send_cart_transcript_to_channel
        transcript_file = await generate_cart_transcript(
            thread=channel,
            bot=bot,
            cart=order,
        )
        if transcript_file:
            await send_cart_transcript_to_channel(
                bot=bot,
                transcript_file=transcript_file,
                channel_id=int(transcript_channel_id),
                cart=order,
            )
    except Exception as e:
        print(f"[RobloxCheckout] Erro ao enviar transcript: {e}")


async def _poll_payment(
    bot,
    channel: disnake.TextChannel,
    order_id: str,
    provider: str,
    payment_data: dict,
    payment_msg: disnake.Message,
    timeout_seconds: int,
    requires_manual_approval: bool = False,
):
    interval = 5
    elapsed = 0

    while elapsed < timeout_seconds:
        await asyncio.sleep(interval)
        elapsed += interval

        order = get_order(order_id)
        if not order:
            return
        if order.get("status") in ("cancelled", "delivered", "payment_approved"):
            return

        # Modo semi-automático (pix_manual): aguardar aprovação via botão pelo admin.
        # O polling apenas monitora cancelamento/timeout — a aprovação não é automática.
        if requires_manual_approval:
            continue

        approved = await _check_payment_status(provider, payment_data)
        if approved:
            update_order(order_id, {"status": "payment_approved"})

            mode = db.get_document("custom_mode").get("mode")
            embed, components, flags = await _build_payment_approved_message(order, mode)

            try:
                await payment_msg.delete()
            except Exception:
                pass

            try:
                if mode == "embed":
                    await channel.send(embed=embed, components=components)
                else:
                    await channel.send(components=components, flags=flags)
            except Exception as e:
                print(f"[RobloxCheckout] Erro ao enviar aprovação: {e}")

            config = get_roblox_config()
            canais = config.get("canais", {})
            canal_vendas_log_id = canais.get("canal_vendas_log")

            if canal_vendas_log_id:
                log_guild = bot.get_guild(order.get("guild_id"))
                if log_guild:
                    log_channel = log_guild.get_channel(int(canal_vendas_log_id))
                    if log_channel:
                        try:
                            roblox_username = order.get("roblox_username", "?")
                            quantity = order.get("quantity", 0)
                            total_price = order.get("payment_data", {}).get("charged_price") or order.get("total_price", 0)
                            order_type = order.get("order_type", "robux")
                            extra = order.get("extra", {})
                            gamepass_name = extra.get("gamepass_name", "")

                            if mode == "embed":
                                log_embed = disnake.Embed(
                                    title="💰 Nova Venda Aprovada",
                                    description=(
                                        f"**Tipo:** `{order_type.title()}`\n"
                                        f"**Comprador:** <@{order.get('user_id')}>\n"
                                        f"**Roblox:** `{roblox_username}`\n"
                                        f"{'**Gamepass:** `' + gamepass_name + '`' + chr(10) if gamepass_name else ''}"
                                        f"**Robux:** `{quantity}`\n"
                                        f"**Valor pago:** `R$ {total_price:.2f}`\n"
                                        f"-# Pedido: `{order_id}`"
                                    ),
                                    color=disnake.Color.green(),
                                )
                                await log_channel.send(embed=log_embed)
                            else:
                                colors = db.get_document("custom_colors") or {}
                                primary_color_hex = colors.get("primary")
                                container_kwargs = {}
                                if primary_color_hex:
                                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                                log_text = (
                                    f"## 💰 Nova Venda Aprovada\n"
                                    f"-# Tipo: `{order_type.title()}` | Pedido: `{order_id}`\n"
                                    f"**Comprador:** <@{order.get('user_id')}> | **Roblox:** `{roblox_username}`\n"
                                    f"{'**Gamepass:** `' + gamepass_name + '`  ' if gamepass_name else ''}"
                                    f"**Robux:** `{quantity}` | **Valor:** `R$ {total_price:.2f}`"
                                )
                                log_components = [
                                    disnake.ui.Container(
                                        disnake.ui.TextDisplay(log_text),
                                        **container_kwargs,
                                    )
                                ]
                                await log_channel.send(
                                    components=log_components,
                                    flags=disnake.MessageFlags(is_components_v2=True),
                                )
                        except Exception as e:
                            print(f"[RobloxCheckout] Erro ao enviar log de venda: {e}")

                        # Notificação por email (fire-and-forget)
                        try:
                            asyncio.create_task(send_sale_email_robux(
                                roblox_user=roblox_username,
                                quantity=quantity,
                                value=float(total_price),
                                order_type=order_type,
                                gamepass_name=gamepass_name,
                            ))
                        except Exception as e:
                            print(f"[Email] Falha ao preparar notificação Robux: {e}")

    # ── Timeout: pagamento expirou ──
    order = get_order(order_id)
    update_order(order_id, {"status": "cancelled"})

    # Gerar transcript antes de fechar
    if order:
        await _try_send_transcript(bot, channel, order)

    try:
        await payment_msg.delete()
    except Exception:
        pass
    try:
        await channel.send("⏰ O pagamento expirou. O ticket será fechado em 30 segundos.")
        await asyncio.sleep(30)
        await channel.delete()
    except Exception:
        pass


class CheckoutRobux(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""

        if custom_id.startswith("RobloxTicket_ContinuarPagamento:"):
            order_id = custom_id.split(":", 1)[1]
            order = get_order(order_id)
            if not order:
                await inter.response.send_message(f"{emoji.wrong} Pedido não encontrado.", ephemeral=True)
                return

            if str(order.get("user_id")) != str(inter.user.id):
                await inter.response.send_message(f"{emoji.wrong} Este botão não é para você.", ephemeral=True)
                return

            if order.get("status") != "pending_payment":
                await inter.response.send_message(f"{emoji.wrong} Este pedido não está aguardando pagamento.", ephemeral=True)
                return

            # Verificar se já existe pagamento em andamento (evitar double-click)
            payment_data = order.get("payment_data") or {}
            if payment_data.get("processing"):
                await inter.response.send_message(f"{emoji.loading} Seu pagamento já está sendo gerado, aguarde...", ephemeral=True)
                return

            provider = _get_active_payment_provider()
            if not provider:
                await inter.response.send_message(f"{emoji.wrong} Nenhum método de pagamento configurado.", ephemeral=True)
                return

            # Marcar como em processamento ANTES de qualquer await longo
            update_order(order_id, {"payment_data": {"processing": True}})

            # Editar a mensagem para "carregando" e desabilitar os botões
            mode = db.get_document("custom_mode").get("mode")
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")

            if mode == "embed":
                await inter.response.edit_message(
                    content=f"{emoji.loading} Gerando seu pagamento, aguarde...",
                    embeds=[],
                    components=[],
                )
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                await inter.response.edit_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"{emoji.loading} Gerando seu pagamento, aguarde..."),
                            **container_kwargs,
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True),
                )

            payment_result, charged_price = await _create_payment(order, provider)
            if not payment_result:
                # Limpar flag de processamento em caso de falha
                update_order(order_id, {"payment_data": {}})
                await inter.followup.send(f"{emoji.wrong} Erro ao gerar pagamento. Contate um administrador.", ephemeral=True)
                return

            copy_code = _extract_copy_code(payment_result)
            qr_bytes = _extract_qr_bytes(payment_result)
            payment_id = _extract_payment_id(payment_result)
            requires_manual_approval = bool(payment_result.get("requires_manual_approval", False)) if payment_result else False

            update_order(order_id, {
                "status": "pending_payment",
                "payment_data": {
                    "provider": provider,
                    "payment_id": payment_id,
                    "copy_code": copy_code,
                    "charged_price": charged_price,
                    "requires_manual_approval": requires_manual_approval,
                    "raw": payment_result,
                }
            })

            mode = db.get_document("custom_mode").get("mode")
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")

            order_type = order.get("order_type", "robux")
            quantity = order.get("quantity", 0)

            # ── Buscar timeout configurado nas preferências ──
            timeout_seconds = _get_cart_timeout_seconds()
            timeout_minutes = timeout_seconds // 60

            files = []
            if qr_bytes:
                files.append(disnake.File(fp=io.BytesIO(qr_bytes), filename="qrcode.png"))

            qr_image_ref = "attachment://qrcode.png" if qr_bytes else None

            cancel_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Cancelar Pagamento",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.wrong,
                    custom_id=f"RobloxTicket_Cancelar:{order_id}",
                ),
            )

            # ── Botão de aprovação manual (semi-automático / pix_manual) ──
            approve_row = None
            if requires_manual_approval:
                approve_row = disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Aprovar Pagamento",
                        style=disnake.ButtonStyle.success,
                        emoji=emoji.double_check if hasattr(emoji, "double_check") else "✅",
                        custom_id=f"RobloxTicket_AprovarPagamento:{order_id}",
                    )
                )

            if mode == "embed":
                embed_color = None
                if primary_color_hex:
                    embed_color = int(primary_color_hex.replace("#", ""), 16)

                embed = disnake.Embed(
                    title=f"{emoji.card} Pagamento PIX — Pendente",
                    description=(
                        f"**Valor:** `R$ {charged_price:.2f}`\n"
                        f"**Tipo:** `{order_type.title()}`\n"
                        f"**Robux:** `{quantity}`\n"
                        f"**Expira em:** `{timeout_minutes} minutos`\n\n"
                        f"{'**PIX Copia e Cola:** (mensagem abaixo)' if copy_code else 'Realize o pagamento para continuar.'}"
                    ),
                )
                if embed_color:
                    embed.color = embed_color
                if qr_image_ref:
                    embed.set_image(url=qr_image_ref)

                embed_components = [cancel_row]
                if approve_row:
                    embed_components.append(approve_row)

                payment_msg = await inter.channel.send(
                    content=f"`{copy_code}`" if copy_code else None,
                    embed=embed,
                    components=embed_components,
                    files=files if files else None,
                )

            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

                inner_items = [
                    disnake.ui.TextDisplay(
                        f"## {emoji.card} Pagamento PIX — Pendente\n"
                        f"-# Valor: `R$ {charged_price:.2f}` | Tipo: `{order_type.title()}` | Robux: `{quantity}`\n"
                        f"-# Expira em: `{timeout_minutes} minutos`\n\n"
                        f"Realize o pagamento via PIX para continuar."
                        + (f"\n\n**PIX Copia e Cola:**\n```\n{copy_code}\n```" if copy_code else "")
                    ),
                ]
                if qr_image_ref:
                    inner_items.append(
                        disnake.ui.MediaGallery(
                            disnake.MediaGalleryItem(media=qr_image_ref)
                        )
                    )
                inner_items.append(disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small))
                inner_items.append(cancel_row)
                if approve_row:
                    inner_items.append(approve_row)

                payment_components = [
                    disnake.ui.Container(
                        *inner_items,
                        **container_kwargs,
                    )
                ]

                payment_msg = await inter.channel.send(
                    components=payment_components,
                    flags=disnake.MessageFlags(is_components_v2=True),
                    files=files if files else None,
                )

            self.bot.loop.create_task(
                _poll_payment(
                    bot=self.bot,
                    channel=inter.channel,
                    order_id=order_id,
                    provider=provider,
                    payment_data=get_order(order_id).get("payment_data", {}),
                    payment_msg=payment_msg,
                    timeout_seconds=timeout_seconds,
                    requires_manual_approval=requires_manual_approval,
                )
            )

        elif custom_id.startswith("RobloxTicket_AprovarPagamento:"):
            order_id = custom_id.split(":", 1)[1]
            order = get_order(order_id)
            if not order:
                await inter.response.send_message(f"{emoji.wrong} Pedido não encontrado.", ephemeral=True)
                return

            # ── Verificar permissão: mesmo padrão do carrinho normal ──
            # Admin do servidor sempre pode; cargo_admin e cargo_suporte também.
            cargos = db.get_document("cargos") or {}
            cargo_admin_id = cargos.get("cargo_admin")
            cargo_suporte_id = cargos.get("cargo_suporte")

            user_roles = [r.id for r in inter.user.roles]
            has_admin_role = cargo_admin_id and int(cargo_admin_id) in user_roles
            has_suporte_role = cargo_suporte_id and int(cargo_suporte_id) in user_roles
            is_guild_admin = inter.user.guild_permissions.administrator

            if not is_guild_admin and not has_admin_role and not has_suporte_role:
                await inter.response.send_message(
                    f"{emoji.wrong} Apenas administradores ou suporte podem aprovar pagamentos.",
                    ephemeral=True,
                )
                return

            if order.get("status") != "pending_payment":
                await inter.response.send_message(
                    f"{emoji.wrong} Este pedido não está aguardando pagamento.",
                    ephemeral=True,
                )
                return

            payment_data = order.get("payment_data") or {}
            provider = payment_data.get("provider", "")
            payment_id = payment_data.get("payment_id")

            # Aprovar no gateway (pix_manual registra a aprovação)
            if provider == "pix_manual" and payment_id:
                try:
                    await approve_manual_pix_payment(payment_id)
                except Exception as e:
                    print(f"[RobloxCheckout] Erro ao aprovar pix_manual: {e}")

            await inter.response.defer(ephemeral=False)

            update_order(order_id, {
                "status": "payment_approved",
                "approved_by": inter.user.id,
            })

            # Recarregar o pedido atualizado para a mensagem de aprovação
            order = get_order(order_id)

            mode = db.get_document("custom_mode").get("mode")
            embed, components, flags = await _build_payment_approved_message(order, mode)

            try:
                await inter.message.edit(embeds=[], components=[])
            except Exception:
                pass

            try:
                if mode == "embed":
                    await inter.channel.send(embed=embed, components=components)
                else:
                    await inter.channel.send(components=components, flags=flags)
            except Exception as e:
                print(f"[RobloxCheckout] Erro ao enviar aprovação manual: {e}")

            # Log de venda
            config = get_roblox_config()
            canais = config.get("canais", {})
            canal_vendas_log_id = canais.get("canal_vendas_log")
            if canal_vendas_log_id:
                log_guild = inter.guild
                log_channel = log_guild.get_channel(int(canal_vendas_log_id)) if log_guild else None
                if log_channel:
                    try:
                        roblox_username = order.get("roblox_username", "?")
                        quantity = order.get("quantity", 0)
                        total_price = payment_data.get("charged_price") or order.get("total_price", 0)
                        order_type = order.get("order_type", "robux")
                        extra = order.get("extra", {})
                        gamepass_name = extra.get("gamepass_name", "")
                        colors = db.get_document("custom_colors") or {}
                        primary_color_hex = colors.get("primary")

                        if mode == "embed":
                            log_embed = disnake.Embed(
                                title="💰 Nova Venda Aprovada",
                                description=(
                                    f"**Tipo:** `{order_type.title()}`\n"
                                    f"**Comprador:** <@{order.get('user_id')}>\n"
                                    f"**Roblox:** `{roblox_username}`\n"
                                    f"{'**Gamepass:** `' + gamepass_name + '`' + chr(10) if gamepass_name else ''}"
                                    f"**Robux:** `{quantity}`\n"
                                    f"**Valor pago:** `R$ {total_price:.2f}`\n"
                                    f"-# Pedido: `{order_id}` | Aprovado por: {inter.user.mention}"
                                ),
                                color=disnake.Color.green(),
                            )
                            await log_channel.send(embed=log_embed)
                        else:
                            container_kwargs = {}
                            if primary_color_hex:
                                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                            log_text = (
                                f"## 💰 Nova Venda Aprovada\n"
                                f"-# Tipo: `{order_type.title()}` | Pedido: `{order_id}`\n"
                                f"**Comprador:** <@{order.get('user_id')}> | **Roblox:** `{roblox_username}`\n"
                                f"{'**Gamepass:** `' + gamepass_name + '`  ' if gamepass_name else ''}"
                                f"**Robux:** `{quantity}` | **Valor:** `R$ {total_price:.2f}`\n"
                                f"-# Aprovado por: {inter.user.mention}"
                            )
                            await log_channel.send(
                                components=[disnake.ui.Container(disnake.ui.TextDisplay(log_text), **container_kwargs)],
                                flags=disnake.MessageFlags(is_components_v2=True),
                            )
                    except Exception as e:
                        print(f"[RobloxCheckout] Erro ao enviar log de aprovação manual: {e}")

                    # Notificação por email (fire-and-forget)
                    try:
                        asyncio.create_task(send_sale_email_robux(
                            roblox_user=roblox_username,
                            quantity=quantity,
                            value=float(total_price),
                            order_type=order_type,
                            gamepass_name=gamepass_name,
                        ))
                    except Exception as e:
                        print(f"[Email] Falha ao preparar notificação Robux manual: {e}")
            order_id = custom_id.split(":", 1)[1]
            order = get_order(order_id)
            if not order:
                await inter.response.send_message(f"{emoji.wrong} Pedido não encontrado.", ephemeral=True)
                return

            user_is_owner = str(order.get("user_id")) == str(inter.user.id)
            user_is_admin = inter.user.guild_permissions.administrator

            if not user_is_owner and not user_is_admin:
                await inter.response.send_message(f"{emoji.wrong} Você não tem permissão para cancelar este pedido.", ephemeral=True)
                return

            update_order(order_id, {"status": "cancelled"})
            await inter.response.send_message(f"{emoji.wrong} Carrinho Cancelado", ephemeral=True)

            # Gerar transcript antes de fechar
            await _try_send_transcript(self.bot, inter.channel, order)

            await asyncio.sleep(3)
            try:
                await inter.channel.delete()
            except Exception:
                pass


def setup(bot: commands.Bot):
    bot.add_cog(CheckoutRobux(bot))