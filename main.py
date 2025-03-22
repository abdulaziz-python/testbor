import asyncio
import logging
import sys
from aiogram import Bot
from bot.loader import dp, setup_middlewares
from config.config import load_config, ConfigError
from bot.utils.database import setup_db
from bot.utils.logger import setup_logger
from bot.handlers.register_handlers import register_handlers

async def main():
    logger = setup_logger()

    try:
        logger.info("Konfiguratsiya yuklanmoqda...")
        config = load_config()

        if not config.bot_token:
            logger.critical("Bot tokeni topilmadi! .env faylini tekshiring.")
            print("❌ XATO: Bot tokeni topilmadi!")
            print(".env faylini yarating va bot tokenini kiriting.")
            print(".env.example faylidan nusxa olishingiz va ma'lumotlarni to'ldirishingiz mumkin.")
            sys.exit(1)

        logger.info("Bot tokeni muvaffaqiyatli yuklandi")

        bot = Bot(token=config.bot_token)

        logger.info("Ma'lumotlar bazasi sozlanmoqda...")
        await setup_db()

        logger.info("Middlewarelar sozlanmoqda...")
        setup_middlewares(dp)

        logger.info("Handlerlar ro'yxatdan o'tkazilmoqda...")
        register_handlers(dp)

        logger.info("Bot ishga tushmoqda...")
        print("✅ Bot ishga tushdi! To'xtatish uchun Ctrl+C tugmalarini bosing.")
        await dp.start_polling(bot)

    except ConfigError as e:
        logger.critical(f"Konfiguratsiya xatosi: {e}")
        print(f"❌ XATO: {e}")
        print(".env faylini tekshiring va barcha kerakli o'zgaruvchilar mavjudligiga ishonch hosil qiling.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Kutilmagan xato: {e}")
        print(f"❌ XATO: Kutilmagan xato yuz berdi: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("👋 Bot foydalanuvchi tomonidan to'xtatildi. Xayr!")

