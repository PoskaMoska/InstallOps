from aiogram import Bot
from app.core.config import settings
from app.core.logging import logger

class TelegramNotifier:
    """
    Service for sending proactive notifications and alerts to Telegram.
    """
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None

    async def send_message(self, text: str) -> bool:
        if not self.bot or not self.chat_id:
            logger.warning("Telegram is not configured. Cannot send message.")
            return False
            
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=text, parse_mode="HTML")
            return True
        except Exception as e:
            logger.error(f"Failed to send telegram message: {e}")
            return False
        finally:
            if self.bot:
                await self.bot.session.close()
