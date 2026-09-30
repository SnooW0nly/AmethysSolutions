from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from functions.database import database as db


def _registrar_usuario(user) -> None:
    """Salva/atualiza o usuário em telegram_users pra permitir broadcast do /anunciar."""
    doc = db.get_document("telegram_users") or {}
    users = doc.setdefault("users", {})
    chat_id = str(user.id)
    existing = users.get(chat_id, {})
    users[chat_id] = {
        "username":    user.username,
        "first_name":  user.first_name,
        "full_name":   user.full_name,
        "first_start": existing.get("first_start") or datetime.utcnow().isoformat(),
        "last_start":  datetime.utcnow().isoformat(),
    }
    db.save_document("telegram_users", {}, doc)


def _montar_texto_start(user, custom: dict) -> str:
    if custom.get("enabled") and custom.get("welcome_message"):
        welcome = custom["welcome_message"].replace("{nome}", user.full_name).replace("{id}", str(user.id))
        final = custom.get("final_text", "O que deseja fazer?")
        return f"{welcome}\n\n{final}"

    return (
        f"👤 *{user.full_name}*\n"
        f"🆔 `{user.id}`\n\n"
        "O que deseja fazer?"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    _registrar_usuario(user)

    saldo_config = db.get_document("loja_saldo_config") or {}
    custom = db.get_document("loja_telegram_customization") or {}

    produtos_label = custom.get("button_produtos_label", "🛍️ Produtos") if custom.get("enabled") else "🛍️ Produtos"
    saldo_label    = custom.get("button_saldo_label", "💰 Saldo") if custom.get("enabled") else "💰 Saldo"

    buttons = [[InlineKeyboardButton(produtos_label, callback_data="produtos")]]
    if saldo_config.get("enabled"):
        buttons[0].append(InlineKeyboardButton(saldo_label, callback_data="saldo"))

    text = _montar_texto_start(user, custom)
    await update.message.reply_text(text, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(buttons))
