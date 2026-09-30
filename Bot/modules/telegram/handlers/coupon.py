from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from functions.loja_products import get_products, format_price_brl
from modules.loja.cart.coupon_validator import CouponValidator
from modules import telegram as tg_module
from modules.telegram import state

AGUARDANDO_CUPOM = 1


async def campo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, product_id, campo_id = query.data.split(":")

    products = get_products() or {}
    product = products.get(product_id)
    campo = product["campos"][campo_id] if product else None
    if not campo:
        await query.edit_message_text("Campo não encontrado.")
        return ConversationHandler.END

    state.set(query.from_user.id, {
        "product_id": product_id,
        "campo_id": campo_id,
        "price": campo["price"],
    })

    buttons = [
        [InlineKeyboardButton("🎟️ Aplicar Cupom", callback_data="cupom_aplicar")],
        [InlineKeyboardButton("➡️ Continuar sem cupom", callback_data="cupom_pular")],
    ]
    await query.edit_message_text(
        f"*{product['name']}* — {campo['name']}\n💰 {format_price_brl(campo['price'])}\n\nDeseja aplicar um cupom?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ConversationHandler.END


async def cupom_aplicar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Digite o código do cupom:")
    return AGUARDANDO_CUPOM


async def cupom_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sess = state.get(user_id)
    code = update.message.text.strip()

    is_valid, error_msg, discount, coupon_data = CouponValidator.validate_product_coupon(
        code, sess["product_id"], f"tg:{user_id}", sess["price"]
    )

    if not is_valid:
        await update.message.reply_text(f"❌ {error_msg}\nDigite outro código ou /start para cancelar.")
        return AGUARDANDO_CUPOM

    final_price = max(0.0, sess["price"] - discount)
    state.update(user_id, coupon_code=code, coupon_data=coupon_data, discount=discount, final_price=final_price)

    await update.message.reply_text(
        f"✅ Cupom *{code}* aplicado!\nDesconto: {format_price_brl(discount)}\nTotal: {format_price_brl(final_price)}",
        parse_mode="Markdown"
    )
    # Segue para pagamento
    from modules.telegram.handlers.payment import iniciar_pagamento
    await iniciar_pagamento(update, context)
    return ConversationHandler.END


async def cupom_pular_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    sess = state.get(user_id)
    state.update(user_id, final_price=sess["price"], discount=0, coupon_code=None, coupon_data=None)

    from modules.telegram.handlers.payment import iniciar_pagamento_query
    await iniciar_pagamento_query(query, context)
    return ConversationHandler.END
