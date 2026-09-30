from telegram import Update
from telegram.ext import ContextTypes
from functions.database import database as db

async def saldo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    doc = db.get_document("telegram_saldo_users") or {}
    users = doc.get("users", {})
    balance = users.get(f"tg:{user_id}", {}).get("balance", 0.0)

    await query.edit_message_text(f"💰 Seu saldo: R$ {balance:.2f}")
