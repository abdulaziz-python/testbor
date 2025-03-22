from typing import Any, Awaitable, Callable, Dict
import time
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from bot.utils.logger import get_logger

logger = get_logger(__name__)

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit=0.5):
        self.limit = limit
        self.user_timeouts = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id
        current_time = time.time()

        if user_id in self.user_timeouts:
            last_time = self.user_timeouts[user_id]
            if current_time - last_time < self.limit:
                logger.info(f"Throttling applied for user {user_id}")
                return None

        self.user_timeouts[user_id] = current_time
        return await handler(event, data)
