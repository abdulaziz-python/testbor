from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.middlewares.subscription import SubscriptionMiddleware
from bot.middlewares.throttling import ThrottlingMiddleware

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def setup_middlewares(dp):
    dp.message.middleware(ThrottlingMiddleware(limit=1))
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
