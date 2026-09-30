import logging
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
from modules.telegram.handlers.start import start
from modules.telegram.handlers.products import produtos_callback, produto_callback
from modules.telegram.handlers.coupon import (
    campo_callback, cupom_aplicar_callback, cupom_pular_callback,
    cupom_texto, AGUARDANDO_CUPOM
)
from modules.telegram.handlers.saldo import saldo_callback
from commands.admin.anunciar.telegram import anunciar_callback_responder

logger = logging.getLogger(__name__)

_app = None

async def start_telegram_bot(token: str, discord_bot=None):
    global _app
    app = ApplicationBuilder().token(token).build()
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(cupom_aplicar_callback, pattern="^cupom_aplicar$")],
        states={
            AGUARDANDO_CUPOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, cupom_texto)],
        },
        fallbacks=[CommandHandler("start", start)]
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(produtos_callback,  pattern="^produtos$"))
    app.add_handler(CallbackQueryHandler(produto_callback,   pattern="^produto:"))
    app.add_handler(CallbackQueryHandler(campo_callback,     pattern="^campo:"))
    app.add_handler(CallbackQueryHandler(cupom_pular_callback, pattern="^cupom_pular$"))
    app.add_handler(CallbackQueryHandler(saldo_callback,     pattern="^saldo$"))
    app.add_handler(CallbackQueryHandler(anunciar_callback_responder, pattern="^anunciar_btn:"))
    app.add_handler(conv_handler)
    _app = app
    if discord_bot is not None:
        discord_bot.telegram_app = app
        app.bot_data["discord_bot"] = discord_bot
    logger.info("[Telegram] Iniciando polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("[Telegram] Polling ativo.")

async def stop_telegram_bot():
    global _app
    if _app:
        try:
            if getattr(_app, "updater", None) and _app.updater.running:
                await _app.updater.stop()
        except RuntimeError:
            pass
        await _app.stop()
        await _app.shutdown()
        _app = None
        logger.info("[Telegram] Bot parado.")
