from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from bot.utils.logger import get_logger
import time
from collections import defaultdict

logger = get_logger(__name__)

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self):
        self.requests = defaultdict(list)
        self.rate_limit = 1
        self.time_window = 1

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user_id = event.from_user.id if isinstance(event, (Message, CallbackQuery)) else None
        if not user_id:
            return await handler(event, data)
        current_time = time.time()
        self.requests[user_id] = [
            t for t in self.requests user_id] if t > current_time - self.time_window
        ]
        if len(self.requests[user_id]) >= self.rate_limit:
            if isinstance(event, Message):
                await event.answer(
                    "⏳ Iltimos, biroz kuting va qayta urinib ko'ring."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⏳ Iltimos, biroz kuting va qayta urinib ko'ring.",
                    show_alert=True
                )
            return
        self.requests[user_id].append(current_time)
        return await handler(event, data)
