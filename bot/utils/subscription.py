from aiogram import Bot
from config.config import load_config
from bot.utils.logger import get_logger

logger = get_logger(__name__)

async def check_subscription(user_id: int, required_channels: list) -> bool:
    config = load_config()
    bot = Bot(token=config.bot_token)

    for channel in required_channels:
        try:
            member = await bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status in ["left", "kicked", "banned"]:
                logger.info(f"User {user_id} is not subscribed to {channel['id']}")
                return False
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id} in channel {channel['id']}: {e}")
            return False

    logger.info(f"User {user_id} is subscribed to all required channels")
    return True
