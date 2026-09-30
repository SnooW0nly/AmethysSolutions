import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from functions.payments.amethys_wallet import create_amethys_payment_from_settings, check_amethys_payment_from_settings
from functions.loja_products import get_products, format_price_brl
from modules.loja.cart.stock_manager import StockManager
from modules.loja.cart.coupon_validator import CouponValidator
from modules.telegram import state
from modules.loja.logs.purchase_logs import PurchaseLogsSystem

logger = logging.getLogger(__name__)

POLL_INTERVAL = 5   # segundos entre checks
POLL_TIMEOUT  = 600 # 10 minutos


async def iniciar_pagamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sess = state.get(user_id)
    if not sess or "product_id" not in sess or "campo_id" not in sess or "final_price" not in sess:
        await update.message.reply_text("❌ Sessão expirada. Use /start e selecione o produto novamente.")
        return
    await _gerar_cobranca(update.message.reply_text, user_id, sess, context)


async def iniciar_pagamento_query(query, context: ContextTypes.DEFAULT_TYPE):
    user_id = query.from_user.id
    sess = state.get(user_id)
    if not sess or "product_id" not in sess or "campo_id" not in sess or "final_price" not in sess:
        await query.edit_message_text("❌ Sessão expirada. Use /start e selecione o produto novamente.")
        return
    await _gerar_cobranca(query.edit_message_text, user_id, sess, context)


async def _gerar_cobranca(send_fn, user_id: int, sess: dict, context):
    try:
        product_id = sess["product_id"]
        campo_id   = sess["campo_id"]
        final_price = sess["final_price"]

        products = get_products() or {}
        product = products.get(product_id, {})
        campo = product.get("campos", {}).get(campo_id, {})

        desc = f"{product.get('name', '')} — {campo.get('name', '')}"

        try:
            payment = await create_amethys_payment_from_settings(final_price, description=desc)
        except Exception as e:
            logger.exception(f"[Telegram] Erro ao criar pagamento para user {user_id} (produto={product_id}, campo={campo_id})")
            await send_fn(f"❌ Erro ao gerar pagamento: {e}")
            return

        if not payment or not payment.get("payment_id"):
            logger.error(f"[Telegram] create_amethys_payment_from_settings retornou vazio/sem payment_id: {payment!r}")
            await send_fn("❌ Erro ao gerar pagamento: resposta inválida do gateway de pagamento.")
            return

        payment_id = payment.get("payment_id")
        pix = payment.get("copy_paste") or payment.get("pix_copia_cola", "")
        qr_url = payment.get("qr_code_url")
        state.update(user_id, payment_id=payment_id)

        msg = (
            f"💳 *Pagamento PIX*\n"
            f"Valor: *{format_price_brl(final_price)}*\n\n"
            f"`{pix}`\n\n"
            f"Aguardando confirmação..."
        )
        if qr_url:
            msg += f"\n[Ver QR Code]({qr_url})"

        await send_fn(msg, parse_mode="Markdown")
        asyncio.create_task(_monitorar_pagamento(user_id, payment_id, product_id, campo_id, sess, context))

    except Exception:
        logger.exception(f"[Telegram] Erro inesperado ao gerar cobrança para user {user_id}")
        try:
            await send_fn("❌ Ocorreu um erro inesperado ao gerar o pagamento. Tente novamente ou use /start.")
        except Exception:
            logger.exception(f"[Telegram] Falha ao notificar user {user_id} sobre erro de cobrança")


async def _monitorar_pagamento(user_id: int, payment_id: str, product_id: str, campo_id: str, sess: dict, context):
    bot = context.bot
    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
        try:
            data = await check_amethys_payment_from_settings(payment_id)
        except Exception as e:
            logger.warning(f"[Telegram] Erro ao checar pagamento {payment_id}: {e}")
            continue

        status = data.get("status", "").lower()
        if status in ("paid", "approved", "completed"):
            await _entregar(bot, user_id, product_id, campo_id, sess)
            return
        if status in ("cancelled", "expired", "failed"):
            await bot.send_message(user_id, "❌ Pagamento cancelado ou expirado.")
            state.clear(user_id)
            return

    await bot.send_message(user_id, "⏱️ Tempo de pagamento expirado.")
    state.clear(user_id)


async def _entregar(bot, user_id: int, product_id: str, campo_id: str, sess: dict):
    items = StockManager.get_stock_items(product_id, campo_id, 1)

    coupon_code = sess.get("coupon_code")
    if coupon_code:
        try:
            CouponValidator.use_product_coupon(product_id, coupon_code, f"tg:{user_id}")
        except Exception as e:
            logger.warning(f"[Telegram] Erro ao marcar cupom usado: {e}")

    products = get_products() or {}
    product = products.get(product_id, {})
    product_name = product.get("name", product_id)
    campo = product.get("campos", {}).get(campo_id, {})
    campo_name = campo.get("name", campo_id)

    if items:
        content = "\n".join(items)
        await bot.send_message(user_id, f"✅ *Compra aprovada!*\n\n{content}", parse_mode="Markdown")
    else:
        await bot.send_message(
            user_id,
            f"✅ Pagamento aprovado! Produto: *{product_name}*\nEntrega manual em breve.",
            parse_mode="Markdown"
        )

    # Log de pedido no Discord
    try:
        from functions.utils import utils as _utils
        if hasattr(bot, "_discord_bot"):
            guild = bot._discord_bot.get_guild(_utils.obter_server_principal())
            if guild:
                logs_cog = bot._discord_bot.get_cog("PurchaseLogsSystem")
                if logs_cog:
                    class _FakeUser:
                        def __init__(self, uid):
                            self.id = uid
                            self.mention = f"Telegram `{uid}`"
                            self.display_name = f"TG:{uid}"
                            self.name = f"tg_{uid}"
                            self.display_avatar = type("a", (), {"url": None})()
                    await logs_cog.send_order_log(
                        guild=guild,
                        user=_FakeUser(user_id),
                        product_name=product_name,
                        campo_name=campo_name,
                        quantity=1,
                        price=sess.get("final_price", 0),
                        payment_method="pix",
                        items=items or [],
                        delivery_type=campo.get("delivery_type", "automatic") if campo else "automatic",
                        source="telegram",
                    )
    except Exception as e:
        logger.warning(f"[Telegram] Erro ao enviar log de pedido: {e}")

    state.clear(user_id)
