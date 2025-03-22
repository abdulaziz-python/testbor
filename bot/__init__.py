from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from .middlewares.throttling import ThrottlingMiddleware
from .middlewares.subscription import SubscriptionMiddleware
from .middlewares.error_handler import ErrorHandler
from bot.utils.logger import get_logger

logger = get_logger(__name__)

def setup_middlewares(dp: Dispatcher):
    # Add all middlewares
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    
    dp.message.middleware(ErrorHandler())
    dp.callback_query.middleware(ErrorHandler())

    logger.info("Middlewares have been set up")