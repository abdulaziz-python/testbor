import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramUnauthorizedError
from bot.handlers import user, admin
from bot.utils.database import init_db
from config.config import load_config

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    try:
        config = load_config()
        
        bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        
        dp.include_router(user.router)
        dp.include_router(admin.router)
        
        await init_db()
        
        try:
            await dp.start_polling(bot)
        except TelegramUnauthorizedError:
            masked_token = f"{config.bot_token[:6]}...{config.bot_token[-6:]}"
            logging.error(f"Xato bot tokeni! Token autentifikatsiyasi xatosi. Bot tokeni: '{masked_token}'")
            logging.error("Botni yaratish uchun @BotFather orqali yangi token oling va .env faylidagi BOT_TOKEN qiymatini yangilang.")
            logging.error("https://t.me/BotFather ga tashrif buyuring va /newbot buyrug'i orqali yangi bot yarating.")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Kutilmagan xato: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped!")
    except (SystemExit, SystemError):
        pass
    except Exception as e:
        logging.error(f"Asosiy xato: {e}")
    finally:
        logging.info("Bot dasturidan chiqildi")

