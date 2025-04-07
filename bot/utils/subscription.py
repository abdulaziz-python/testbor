import aiohttp
from typing import List, Dict
from bot.utils.logger import get_logger

logger = get_logger(__name__)

async def check_subscription(user_id: int, channels: List[Dict[str, str]]):
    """Foydalanuvchi barcha kanallarga a'zo bo'lganligini tekshirish"""
    
    if not channels:
        return True  # Agar kanallar ro'yxati bo'sh bo'lsa, tekshirish o'tkazildi

    try:
        # Bitta ClientSession yaratamiz va har bir kanal uchun foydalanmiz
        async with aiohttp.ClientSession() as session:
            for channel in channels:
                channel_id = channel["id"]
                
                # API so'rovini yuborish
                async with session.get(
                    f"https://api.telegram.org/bot{channel['token']}/getChatMember",
                    params={"chat_id": channel_id, "user_id": user_id}
                ) as response:
                    if response.status != 200:
                        # API xatosi
                        logger.error(f"API error: {response.status} - {await response.text()}")
                        continue
                    
                    result = await response.json()
                    
                    if not result.get("ok", False):
                        # API xatosi
                        logger.error(f"API error: {result}")
                        continue
                    
                    status = result.get("result", {}).get("status", "")
                    
                    # "left", "kicked" yoki "restricted" (restrictions ban_in_all_groups bo'lsa)
                    if status in ["left", "kicked"] or (
                        status == "restricted" and not result.get("result", {}).get("can_send_messages", True)
                    ):
                        logger.info(f"User {user_id} is not subscribed to channel {channel_id}")
                        return False
            
            logger.info(f"User {user_id} is subscribed to all required channels")
            return True
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        return True  # Xato bo'lganda, tekshirishni o'tkazilgan deb hisoblaymiz
