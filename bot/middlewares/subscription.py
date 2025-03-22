from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.filters import Command
from bot.utils.subscription import check_subscription
from config.config import load_config
from bot.keyboards.inline import create_subscription_keyboard
from bot.utils.logger import get_logger

logger = get_logger(__name__)

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        config = load_config()

        # Always allow these commands and callbacks
        if isinstance(event, Message) and event.text:
            if event.text.startswith(('/start', '/help', '/admin')):
                return await handler(event, data)

        if isinstance(event, CallbackQuery):
            if event.data in ["check_subscription", "help", "back_to_main"]:
                return await handler(event, data)
            user_id = event.from_user.id
            message = event.message
        elif isinstance(event, Message):
            user_id = event.from_user.id
            message = event
        else:
            return await handler(event, data)

        # Check subscription
        is_subscribed = await check_subscription(user_id, config.required_channels)

        if is_subscribed:
            return await handler(event, data)
        else:
            # Handle non-subscribed users
            if isinstance(event, Message):
                await message.answer(
                    "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:",
                    reply_markup=create_subscription_keyboard(config.required_channels)
                )
                logger.info(f"User {user_id} is not subscribed to required channels")
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⚠️ Botdan foydalanish uchun barcha kanallarga obuna bo'lishingiz kerak.",
                    show_alert=True
                )
                await message.edit_text(
                    "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:",
                    reply_markup=create_subscription_keyboard(config.required_channels)
                )
                logger.info(f"User {user_id} tried to use callback but is not subscribed")

            return None
