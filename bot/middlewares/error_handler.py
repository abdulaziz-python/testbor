from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.utils.logger import get_logger
from config.config import load_config

logger = get_logger(__name__)
config = load_config()

class ErrorHandlerMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error in handler: {e}", exc_info=True)
            if hasattr(event, 'message') and event.message:
                await event.message.answer(
                    "❌ Botda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning: @y0rdam_42"
                )
            elif hasattr(event, 'callback_query') and event.callback_query:
                await event.callback_query.message.edit_text(
                    "❌ Botda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning: @y0rdam_42",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", url="https://t.me/y0rdam_42")]
                    ])
                )
            for admin_id in config.admin_ids:
                try:
                    await event.bot.send_message(
                        admin_id,
                        f"🚨 Xatolik yuz berdi!\n\n"
                        f"Foydalanuvchi: {event.from_user.id}\n"
                        f"Xatolik: {str(e)}\n"
                        f"Handler: {handler.__name__}\n"
                        f"Event: {event.__class__.__name__}"
                    )
                except Exception as admin_e:
                    logger.error(f"Error notifying admin {admin_id}: {admin_e}", exc_info=True)
            raise
