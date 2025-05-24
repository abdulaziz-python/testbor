import asyncio
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from bot.handlers.register_handlers import register_handlers
from bot.utils.logger import get_logger
from bot.utils.database import init_db
from config.config import load_config
import ssl
import hmac
import hashlib
import json

logger = get_logger(__name__)
config = load_config()

async def crypto_webhook_handler(request: web.Request):
    try:
        payload = await request.json()
        secret_key = config.crypto_pay_token.encode('utf-8')
        signature = request.headers.get('Crypto-Pay-API-Signature')
        if not signature:
            logger.error("Webhook signature missing")
            return web.Response(status=400, text="Signature missing")
        data = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        computed_signature = hmac.new(secret_key, data, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed_signature, signature):
            logger.error("Invalid webhook signature")
            return web.Response(status=403, text="Invalid signature")
        update_type = payload.get("update_type")
        if update_type != "invoice_paid":
            return web.Response(status=200, text="OK")
        invoice = payload.get("payload", {})
        invoice_status = invoice.get("status")
        if invoice_status != "paid":
            return web.Response(status=200, text="OK")
        custom_payload = invoice.get("payload", "")
        if not custom_payload.startswith("premium_"):
            return web.Response(status=200, text="OK")
        user_id = int(custom_payload.split("_")[1])
        amount = float(invoice.get("amount", 0))
        currency = invoice.get("asset", "")
        bot = request.app["bot"]
        from bot.utils.database import set_premium_status, update_payment_status, get_user
        from cachetools import TTLCache
        user_cache = TTLCache(maxsize=1000, ttl=300)
        await set_premium_status(user_id, True)
        payment_id = f"crypto_{user_id}_{custom_payload}"
        await update_payment_status(payment_id, "completed")
        user = user_cache.get(user_id) or await get_user(user_id)
        user_cache[user_id] = user
        username = user["username"] if user else "Noma'lum"
        full_name = user["full_name"] if user else "Noma'lum"
        payment_info = {
            "amount": amount,
            "currency": currency,
            "method": f"Crypto to'lov ({currency})",
            "payment_id": payment_id,
            "status": "Muvaffaqiyatli"
        }
        for admin_id in config.admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    f"💰 Yangi to'lov qabul qilindi!\n\n"
                    f"👤 Foydalanuvchi: {full_name} (@{username})\n"
                    f"🆔 ID: {user_id}\n"
                    f"💵 Miqdor: {amount} {currency}\n"
                    f"💳 To'lov usuli: {payment_info['method']}\n"
                    f"🕒 Sana: {payload.get('update_time', '')}\n"
                    f"🔑 To'lov ID: {payment_id}\n\n"
                    f"✅ Status: Muvaffaqiyatli"
                )
            except Exception as e:
                logger.error(f"Error notifying admin {admin_id}: {e}", exc_info=True)
        try:
            await bot.send_message(
                user_id,
                "🎉 Tabriklaymiz! Premium obuna muvaffaqiyatli faollashtirildi!\n\n"
                "• Cheksiz testlar yaratish imkoniyatiga ega bo'ldingiz\n"
                "• Har bir testda 100 tagacha savol yaratish mumkin\n\n"
                "✅ To'lovingiz uchun rahmat!"
            )
        except Exception as e:
            logger.error(f"Error notifying user {user_id}: {e}", exc_info=True)
        return web.Response(status=200, text="OK")
    except Exception as e:
        logger.error(f"Error in crypto_webhook_handler: {e}", exc_info=True)
        return web.Response(status=500, text="Internal Server Error")

async def on_startup(dp: Dispatcher, bot: Bot):
    try:
        await init_db()
        await bot.set_webhook(
            url=f"https://{config.webhook_domain}{config.webhook_path}",
            certificate=open(config.ssl_cert, 'rb') if config.ssl_cert else None,
            drop_pending_updates=True
        )
        logger.info("Webhook set successfully")
    except Exception as e:
        logger.error(f"Error on startup: {e}", exc_info=True)

async def on_shutdown(dp: Dispatcher, bot: Bot):
    try:
        await bot.delete_webhook()
        logger.info("Webhook deleted successfully")
    except Exception as e:
        logger.error(f"Error on shutdown: {e}", exc_info=True)

def main():
    bot = Bot(token=config.bot_token, parse_mode="HTML")
    dp = Dispatcher()
    register_handlers(dp)
    app = web.Application()
    webhook_path = config.webhook_path
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
    app.router.add_post("/crypto_webhook", crypto_webhook_handler)
    app["bot"] = bot
    app.on_startup.append(lambda _: on_startup(dp, bot))
    app.on_shutdown.append(lambda _: on_shutdown(dp, bot))
    setup_application(app, dp, bot=bot)
    ssl_context = None
    if config.ssl_cert and config.ssl_key:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(config.ssl_cert, config.ssl_key)
    web.run_app(
        app,
        host=config.webserver_host,
        port=config.webserver_port,
        ssl_context=ssl_context
    )

if __name__ == "__main__":
    main()
