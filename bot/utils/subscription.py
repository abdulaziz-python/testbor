from aiogram import Bot
from bot.utils.logger import get_logger
from config.config import load_config

logger = get_logger(__name__)
config = load_config()

async def check_subscription(user_id, channels):
    bot = Bot.get_current()
    if not bot:
        bot = Bot(token=config.bot_token)
    try:
        for channel in channels:
            chat_member = await bot.get_chat_member(channel["id"], user_id)
            if chat_member.status in ["left", "kicked"]:
                return False
        return True
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}", exc_info=True)
        return False
    finally:
        if not Bot.get_current():
            await bot.session.close()
