from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from functions.loja_products import get_products, format_price_brl
from functions.database import database as db
from modules.loja.cart.stock_manager import StockManager

async def produtos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    products = get_products() or {}
    buttons = []
    for pid, p in products.items():
        if not p.get("info", {}).get("telegram_enabled"):
            continue
        buttons.append([InlineKeyboardButton(p["name"], callback_data=f"produto:{pid}")])

    if not buttons:
        await query.edit_message_text("Nenhum produto disponível no momento.")
        return

    custom = db.get_document("loja_telegram_customization") or {}
    header = custom.get("produtos_header", "🛍️ *Produtos disponíveis:*") if custom.get("enabled") else "🛍️ *Produtos disponíveis:*"

    await query.edit_message_text(header, parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(buttons))


async def produto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    product_id = query.data.split(":")[1]

    products = get_products() or {}
    product = products.get(product_id)
    if not product:
        await query.edit_message_text("Produto não encontrado.")
        return

    campos = product.get("campos", {})
    buttons = []
    for cid, campo in campos.items():
        stock = StockManager.get_available_stock(product_id, cid)
        infinite = campo.get("infinite_stock", {}).get("enabled", False)
        if not infinite and stock <= 0:
            continue
        label = f"{campo['name']} — {format_price_brl(campo['price'])}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"campo:{product_id}:{cid}")])

    if not buttons:
        await query.edit_message_text("Nenhuma opção disponível para este produto.")
        return

    buttons.append([InlineKeyboardButton("⬅️ Voltar", callback_data="produtos")])
    await query.edit_message_text(f"📦 *{product['name']}*\nEscolha uma opção:",
                                   parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup(buttons))
