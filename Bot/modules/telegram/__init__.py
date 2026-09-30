import asyncio
import logging
import disnake
from disnake.ext import commands
from modules.settings.telegram.cog import TelegramConfig

logger = logging.getLogger(__name__)


class TelegramRunner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._started = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._started:
            return
        self._started = True

        config = TelegramConfig.get_config()
        if not config.get("validated") or not config.get("token"):
            logger.info("[Telegram] Token não configurado, bot do Telegram não iniciado.")
            return

        from modules.telegram.runner import start_telegram_bot
        asyncio.create_task(start_telegram_bot(config["token"], self.bot))


def setup(bot):
    bot.add_cog(TelegramRunner(bot))
