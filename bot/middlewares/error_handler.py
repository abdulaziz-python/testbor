from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from typing import Callable, Dict, Any, Awaitable
from bot.utils.logger import get_logger
from bot.keyboards.inline import create_back_keyboard

logger = get_logger(__name__)

class ErrorHandler(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramBadRequest as e:
            if "BUTTON_DATA_INVALID" in str(e):
                logger.error(f"Button data invalid error: {e}")
                if isinstance(event, CallbackQuery) and event.message:
                    await event.message.edit_text(
                        "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                        reply_markup=create_back_keyboard("back_to_admin")
                    )
                elif isinstance(event, Message):
                    await event.answer(
                        "Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                        reply_markup=create_back_keyboard("back_to_admin")
                    )
            else:
                logger.error(f"Telegram bad request error: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error in middleware: {e}")
            raise