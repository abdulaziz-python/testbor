from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from bot.utils.subscription import check_subscription
from bot.keyboards.inline import create_subscription_keyboard
from config.config import load_config
from bot.utils.logger import get_logger

logger = get_logger(__name__)
config = load_config()

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        if isinstance(event, (Message, CallbackQuery)):
            user_id = event.from_user.id
            exempt_commands = ["/start", "/help"]
            if isinstance(event, Message) and event.text in exempt_commands:
                return await handler(event, data)
            if isinstance(event, CallbackQuery) and event.data in ["check_subscription", "back_to_main", "help", "contact_admin"]:
                return await handler(event, data)
            try:
                is_subscribed = await check_subscription(user_id, config.required_channels)
                if not is_subscribed:
                    text = "Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:"
                    if isinstance(event, Message):
                        await event.answer(
                            text,
                            reply_markup=create_subscription_keyboard(config.required_channels)
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.message.edit_text(
                            text,
                            reply_markup=create_subscription_keyboard(config.required_channels)
                        )
                    return
            except Exception as e:
                logger.error(f"Error in subscription check for user {user_id}: {e}", exc_info=True)
                if isinstance(event, Message):
                    await event.answer(
                        "Xatolik yuz berdi. Iltimos, admin bilan bog'laning: @yordam_42"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.message.edit_text(
                        "Xatolik yuz berdi. Iltimos, admin bilan bog'laning: @yordam_42",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", url="https://t.me/yordam_42")]
                        ])
                    )
        return await handler(event, data)
