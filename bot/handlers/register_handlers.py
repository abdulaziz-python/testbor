from aiogram import Dispatcher
from bot.handlers.user import router as user_router
from bot.handlers.admin import router as admin_router
from bot.middlewares.error_handler import ErrorHandlerMiddleware
from bot.middlewares.subscription import SubscriptionMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware

def register_handlers(dp: Dispatcher):
    dp.message.middleware(ErrorHandlerMiddleware())
    dp.callback_query.middleware(ErrorHandlerMiddleware())
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.include_router(user_router)
    dp.include_router(admin_router)
