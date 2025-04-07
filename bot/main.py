import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Update, WebhookInfo
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import json

from bot.handlers import user, admin
from bot.middleware.subscription import CheckSubscriptionMiddleware
from config.config import load_config
from bot.utils.database import init_db, set_premium_status, update_payment_status
from bot.utils.logger import get_logger
from bot.utils.crypto_pay import CryptoPayAPI

logger = get_logger(__name__)

# Webhook endpointi
WEBHOOK_PATH = "/webhook"
CRYPTO_WEBHOOK_PATH = "/cryptopay/webhook"

# Asosiy router
main_router = Router()
main_router.include_router(user.router)
main_router.include_router(admin.router)

# Bot sozlanishi
async def on_startup(bot: Bot) -> None:
    config = load_config()
    
    # Bot webhookni o'rnatish
    webhook_url = config.webhook_url
    if webhook_url:
        await bot.set_webhook(url=webhook_url + WEBHOOK_PATH)
        logger.info(f"Webhook established at {webhook_url + WEBHOOK_PATH}")

    # Ma'lumotlar bazasini yaratish
    await init_db()

async def on_shutdown(bot: Bot) -> None:
    # Webhook o'chirish
    await bot.delete_webhook()
    logger.info("Webhook deleted")

async def main() -> None:
    config = load_config()
    
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    
    # Middleware qo'shish
    dp.message.middleware(CheckSubscriptionMiddleware())
    dp.callback_query.middleware(CheckSubscriptionMiddleware())
    
    # Router qo'shish
    dp.include_router(main_router)
    
    # Bot WebApp uchun webhook sozlash
    if config.webhook_url:
        logger.info("Using webhook mode")
        app = web.Application()
        
        # Webhook handler
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_handler.register(app, path=WEBHOOK_PATH)
        
        @web.middleware
        async def handle_exceptions(request, handler):
            try:
                return await handler(request)
            except Exception as e:
                logger.error(f"Middleware caught error: {e}")
                return web.json_response({
                    "error": f"Server error: {str(e)}"
                }, status=500)
                
        app.middlewares.append(handle_exceptions)
        
        # Crypto webhook handler
        async def crypto_webhook_handler(request):
            try:
                logger.info("Received crypto webhook request")
                
                # Tekshirish
                if not request.body_exists:
                    logger.warning("Empty request body for crypto webhook")
                    return web.json_response({"status": "error", "message": "Empty request"}, status=400)
                
                data = await request.json()
                logger.info(f"Received CryptoPay webhook: {data}")
                
                # Webhook xavfsizligini tekshirish
                # TODO: Implement proper webhook verification
                
                # Invoice statusini tekshirish
                if data.get("update_type") == "invoice_paid":
                    invoice_data = data.get("payload", {})
                    invoice_id = invoice_data.get("invoice_id")
                    asset = invoice_data.get("asset")
                    amount = invoice_data.get("amount")
                    payload = invoice_data.get("payload", "")
                    
                    logger.info(f"Invoice paid: {invoice_id}, {asset}, {amount}, payload: {payload}")
                    
                    # Payload formatini tekshirish: premium_USER_ID_RANDOM
                    if payload and payload.startswith("premium_"):
                        try:
                            parts = payload.split("_")
                            if len(parts) >= 2:
                                user_id = int(parts[1])
                                
                                # Foydalanuvchini premium qilish
                                await set_premium_status(user_id, True)
                                
                                # To'lov maqomini yangilash
                                await update_payment_status(payload, "completed")
                                
                                # Foydalanuvchiga xabar yuborish
                                try:
                                    await bot.send_message(
                                        chat_id=user_id,
                                        text=f"🎉 Tabriklaymiz! {asset} orqali to'lovingiz muvaffaqiyatli amalga oshirildi."
                                             f"\n\nPremium imkoniyatlar faollashtirildi!"
                                    )
                                    logger.info(f"Successfully activated premium for user {user_id}")
                                    
                                    # Adminlarga xabar yuborish
                                    from bot.handlers.user import notify_admins_about_payment
                                    payment_info = {
                                        "amount": float(amount),
                                        "currency": asset,
                                        "method": f"Crypto to'lov ({asset})",
                                        "payment_id": payload,
                                        "status": "Muvaffaqiyatli"
                                    }
                                    await notify_admins_about_payment(bot, user_id, payment_info)
                                except Exception as e:
                                    logger.error(f"Error sending confirmation to user {user_id}: {e}")
                        except (ValueError, IndexError) as e:
                            logger.error(f"Error parsing payload {payload}: {e}")
                            return web.json_response({"status": "error", "message": f"Invalid payload format: {payload}"}, status=400)
                    else:
                        logger.warning(f"Unknown payload format: {payload}")
                else:
                    logger.info(f"Received non-payment webhook update: {data.get('update_type')}")
                
                return web.json_response({"status": "success"})
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in crypto webhook: {e}")
                return web.json_response({"status": "error", "message": "Invalid JSON"}, status=400)
            except Exception as e:
                logger.error(f"Error processing crypto webhook: {e}")
                return web.json_response({"status": "error", "message": str(e)}, status=500)
        
        # Webhook yo'lini ro'yxatga olish
        app.router.add_post(CRYPTO_WEBHOOK_PATH, crypto_webhook_handler)
        
        # Startup va shutdown
        app.on_startup.append(lambda app: asyncio.create_task(on_startup(bot)))
        app.on_shutdown.append(lambda app: asyncio.create_task(on_shutdown(bot)))
        
        # Web serverini ishga tushirish
        web_server_host = config.web_server_host if hasattr(config, 'web_server_host') else "0.0.0.0"
        web_server_port = config.web_server_port if hasattr(config, 'web_server_port') else 8000
        
        logger.info(f"Starting webhook server on {web_server_host}:{web_server_port}")
        
        # Serverga sozlamalarni qo'llash
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=web_server_host, port=web_server_port)
        
        # Serverni ishga tushirish
        await site.start()
        
        # Bot o'chirish signalini kutish
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Bot stopping...")
    else:
        logger.info("Using polling mode")
        await on_startup(bot)
        await dp.start_polling(bot)
        await on_shutdown(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.warning("Bot stopped!")
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True) 