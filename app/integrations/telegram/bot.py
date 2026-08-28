import asyncio
from aiogram import Bot, Dispatcher
from app.core.config import settings
from app.integrations.telegram.handlers import router
from app.core.logging import logger

def get_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp

async def start_bot():
    """
    Entrypoint for the Telegram bot polling process.
    Designed to run as a background task or in a separate worker.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot will not start.")
        return
        
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = get_dispatcher()
    
    logger.info("Starting Telegram Bot polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Telegram bot polling crashed: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(start_bot())
