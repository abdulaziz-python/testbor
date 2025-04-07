from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, SuccessfulPayment, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction  
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import asyncio
import math
import uuid
import os
import tempfile
import datetime


from bot.keyboards.inline import (
    create_main_keyboard, create_subscription_keyboard,
    create_skip_keyboard, create_back_keyboard,
    create_premium_keyboard, create_pagination_keyboard,
    create_payment_options_keyboard, get_premium_prices, 
    get_premium_plus_prices, create_crypto_payment_options_keyboard,
    create_contact_admin_keyboard
)
from bot.utils.database import (
    register_user, get_user, update_test_count,
    save_test_info, get_user_tests, get_user_stars, 
    add_user_stars, spend_stars_for_premium, set_premium_status,
    record_payment, update_payment_status
)
from bot.utils.document import generate_test_document
from bot.utils.subscription import check_subscription
from bot.utils.logger import get_logger
from bot.utils.crypto_pay import CryptoPayAPI, test_crypto_pay
from config.config import load_config

logger = get_logger(__name__)
router = Router()

config = load_config()
PAYMENT_PROVIDER_TOKEN = config.payment_token

class TestGeneration(StatesGroup):
    waiting_for_subject = State()
    waiting_for_description = State()
    waiting_for_questions_count = State()

class PromoCodeState(StatesGroup):
    waiting_for_code = State()

def create_contact_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", url="https://t.me/y0rdam42")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
    ])

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""
    
    try:
        await register_user(user_id, username, full_name)
        
        await message.answer(
            f"👋 Assalomu alaykum, {full_name}!\n\n"
            "🤖 Men TestBor botman - test yaratish uchun bot.\n\n"
            "📝 Turli fanlar bo'yicha testlar yaratishingiz mumkin\n"
            "💾 Testlar Word formatida yuklab beriladi\n"
            "⭐️ Test yaratib yulduzlar yig'ing va Premium olish uchun sarflang\n\n"
            "Boshlash uchun «Test yaratish» tugmasini bosing!",
            reply_markup=create_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(
            "Botda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning: @yordam_42",
            reply_markup=create_main_keyboard()
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Yordam: Bu bot turli fanlar bo'yicha test yaratishda yordam beradi.\n"
        "• Test yaratish uchun 'Test yaratish' tugmasini bosing\n"
        "• Oddiy foydalanuvchilar har bir testda 30 tagacha savol yarata oladi\n"
        "• Premium foydalanuvchilar cheksiz testlar va har bir testda 100 tagacha savol yarata oladi\n"
        "Savollaringiz bo'lsa, admin bilan bog'laning: @yordam_42",
        reply_markup=create_back_keyboard()
    )

@router.callback_query(F.data == "check_subscription")
async def process_check_subscription(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id

    config = load_config()
    is_subscribed = await check_subscription(user_id, config.required_channels)

    if is_subscribed:
        await callback_query.message.edit_text(
            "✅ Obuna bo'lganingiz uchun rahmat!\n\nEndi botning barcha imkoniyatlaridan foydalanishingiz mumkin.",
            reply_markup=create_main_keyboard()
        )
    else:
        await callback_query.answer(
            "❌ Botdan foydalanish uchun barcha kanallarga obuna bo'lishingiz kerak.",
            show_alert=True
        )

@router.callback_query(F.data == "generate_test")
async def process_generate_test(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    config = load_config()
    is_subscribed = await check_subscription(user_id, config.required_channels)

    if not is_subscribed:
        await callback_query.answer(
            "❌ Botdan foydalanish uchun barcha kanallarga obuna bo'lishingiz kerak.",
            show_alert=True
        )
        await callback_query.message.edit_text(
            "Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:",
            reply_markup=create_subscription_keyboard(config.required_channels)
        )
        return

    user = await get_user(user_id)
    if user:
        tests_generated = user[6] or 0
        test_limit = user[5] or 30
        is_premium = user[4] == 1

        if tests_generated >= test_limit and not is_premium:
            stars = await get_user_stars(user_id) or 0
            stars_cost = 100
            stars_discount = 10
            discounted_cost = stars_cost - stars_discount
            
            await callback_query.answer(
                "⚠️ Siz bepul test limitiga yetdingiz!",
                show_alert=True
            )
            
            await callback_query.message.edit_text(
                f"🔒 Sizning test limitingiz tugadi!\n\n"
                f"Siz allaqachon {tests_generated} ta test yaratdingiz, bu sizning {test_limit} ta limitingizga teng.\n\n"
                f"Cheksiz testlar yaratish uchun quyidagi variantlar mavjud:\n"
                f"• 💫 Premium obuna: har bir testda 100 tagacha savol, cheksiz testlar\n"
                f"• ⭐️ Maxsus taklif: {stars_discount} yulduz chegirma bilan {discounted_cost} yulduz (oddiy narxi {stars_cost})\n\n"
                f"Hozirgi yulduzlaringiz: {stars}",
                reply_markup=create_premium_keyboard()
            )
            return

    await callback_query.message.edit_text(
        "📚 Qaysi fan bo'yicha test yaratmoqchisiz?\nMasalan: Matematika, Tarix, Biologiya va hokazo."
    )

    await state.set_state(TestGeneration.waiting_for_subject)

@router.message(TestGeneration.waiting_for_subject)
async def process_subject(message: Message, state: FSMContext):
    subject = message.text

    await state.update_data(subject=subject)

    await message.answer(
        "📝 Iltimos, test uchun qisqacha tavsif yoki mavzuni kiriting (ixtiyoriy).\n\n"
        "Masalan: 'Algebra tenglamalari' yoki 'Ikkinchi jahon urushi'",
        reply_markup=create_skip_keyboard()
    )

    await state.set_state(TestGeneration.waiting_for_description)

@router.callback_query(F.data == "skip_description")
async def process_skip_description(callback_query: CallbackQuery, state: FSMContext):
    await state.update_data(description="")

    user_id = callback_query.from_user.id
    user = await get_user(user_id)

    max_questions = 30
    if user and user[4] == 1:
        max_questions = 100

    await callback_query.message.edit_text(
        f"🔢 Testda nechta savol bo'lishini xohlaysiz? (1-{max_questions})"
    )

    await state.set_state(TestGeneration.waiting_for_questions_count)

@router.message(TestGeneration.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    description = message.text

    await state.update_data(description=description)

    user_id = message.from_user.id
    user = await get_user(user_id)

    max_questions = 30
    if user and user[4] == 1:
        max_questions = 100

    await message.answer(f"🔢 Testda nechta savol bo'lishini xohlaysiz? (1-{max_questions})")

    await state.set_state(TestGeneration.waiting_for_questions_count)

@router.message(TestGeneration.waiting_for_questions_count)
async def process_questions_count(message: Message, state: FSMContext):
    try:
        questions_count = int(message.text)

        user_id = message.from_user.id
        user = await get_user(user_id)

        max_questions = 30
        if user and user[4] == 1:  
            max_questions = 100

        if questions_count < 1 or questions_count > max_questions:
            await message.answer(f"❌ Iltimos, 1 dan {max_questions} gacha bo'lgan son kiriting.")
            return

        data = await state.get_data()
        subject = data.get("subject")
        description = data.get("description", "")

        await message.answer("🚀 Test soniyalar ichida tayyor bo'ladi, kutishga xojat yo'q!")
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

        earned_stars = 0
        if questions_count <= 10:
            earned_stars = 2
        elif questions_count <= 20:
            earned_stars = 5
        else:
            earned_stars = 10

        test_file = await generate_test_document(subject, description, questions_count)

        if test_file:
            await update_test_count(user_id)
            await save_test_info(user_id, subject, description, questions_count)

            await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_DOCUMENT)
            
            temp_file = tempfile.NamedTemporaryFile(suffix='.docx', delete=False)
            temp_filename = temp_file.name
            temp_file.write(test_file.getvalue())
            temp_file.close()
            
            with open(temp_filename, 'rb') as file:
                await message.answer_document(
                    document=BufferedInputFile(file.read(), filename=f"{subject}_test.docx"),
                    caption=(
                        f"✅ {subject} bo'yicha test\n"
                        f"📊 {questions_count} ta savol\n"
                        f"❗️ Test yaratildi."
                    )
                )
            
            try:
                os.unlink(temp_filename)
            except Exception as e:
                logger.error(f"Error deleting temp file: {e}")

            if earned_stars > 0:
                await add_user_stars(user_id, earned_stars)
                current_stars = await get_user_stars(user_id) or 0
                await message.answer(
                    f"✨ Tabriklaymiz! {earned_stars} ta yulduz qo'shildi.\n"
                    f"💫 Jami yulduzlaringiz: {current_stars}\n\n"
                    f"ℹ️ Premium olish uchun {100 - current_stars} ta yulduz kerak bo'ladi."
                )

            is_premium = user and user[4] == 1
            if is_premium:
                premium_text = "Siz Premium foydalanuvchisiz! 💎"
            else:
                tests_generated = user[6] if user else 0
                test_limit = user[5] if user else 30
                tests_left = max(0, test_limit - tests_generated - 1)
                premium_text = f"Qolgan bepul testlar: {tests_left} ta"

            await message.answer(
                f"📋 Test yaratish muvaffaqiyatli yakunlandi!\n"
                f"{premium_text}\n\n"
                "Yana test yaratishni xohlaysizmi?",
                reply_markup=create_main_keyboard()
            )
        else:
            await message.answer(
                "❌ Test yaratishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning.",
                reply_markup=create_contact_admin_keyboard()
            )

    except ValueError:
        await message.answer(
            "❌ Iltimos, to'g'ri son kiriting.",
            reply_markup=create_back_keyboard()
        )
    except Exception as e:
        logger.error(f"Error generating test: {e}")
        await message.answer(
            "❌ Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning.",
            reply_markup=create_contact_admin_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "premium")
async def process_premium(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    stars = await get_user_stars(user_id) or 0
    stars_cost = 100
    stars_discount = 10
    discounted_cost = stars_cost - stars_discount
    
    await callback_query.message.edit_text(
        "💫 Premium imkoniyatlari:\n\n"
        "• 🧪 Har bir testda 💯 tagacha savol yaratish\n"
        "• ✨ Cheksiz miqdorda testlar yaratish\n"
        "• 🏆 Yuqori sifatli testlar yaratish\n"
        "• 🆘 Ustuvor yordam\n\n"
        f"Sizning hozirgi yulduzlaringiz: {stars} ⭐️\n"
        f"💥 MAXSUS TAKLIF: {stars_discount} yulduz chegirma!\n"
        f"Premium narxi: {discounted_cost} yulduz (asosiy narx: {stars_cost} yulduz)\n\n"
        "Quyidagi usullardan birini tanlang:",
        reply_markup=create_premium_keyboard()
    )

@router.callback_query(F.data == "buy_premium_crypto")
async def process_buy_premium_crypto(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "💎 Crypto orqali to'lov qilish uchun valyutani tanlang:\n\n"
        "• 💱 USDT: 3$ (TRC-20 tarmog'ida)\n"
        "• 💰 TON: 0.6 TON\n\n"
        "⚠️ Agar to'lov bilan muammo bo'lsa, admin bilan bog'laning\n"
        "Eslatma: To'lov muvaffaqiyatli amalga oshirilgandan so'ng, premium avtomatik faollashtiriladi.",
        reply_markup=create_crypto_payment_options_keyboard()
    )

@router.callback_query(F.data == "crypto_premium_usdt_5")
async def process_crypto_premium_usdt(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    payload = f"premium_{user_id}_{uuid.uuid4().hex[:8]}"
    
    try:
        await callback_query.answer("To'lov tayyorlanmoqda...")
        
        crypto_pay = CryptoPayAPI()
        invoice = await crypto_pay.create_invoice(
            asset="USDT",
            amount="3.0",
            description="Premium obuna - TestBor bot",
            hidden_message="Premium obuna uchun rahmat! Endi testlarni cheksiz yaratishingiz mumkin.",
            paid_btn_name="callback",
            paid_btn_url=f"https://t.me/testbor_bot?start=payment_{payload}",
            payload=payload,
            allow_comments=True,
            allow_anonymous=False,
            expires_in=24 * 60 * 60
        )
        
        if "error" in invoice:
            logger.error(f"Error creating crypto invoice: {invoice['error']}")
            await callback_query.message.edit_text(
                "❌ To'lov tizimida xatolik yuz berdi.\n\n"
                f"Xatolik: {invoice.get('error')}\n\n"
                "Iltimos, boshqa to'lov usulini tanlang yoki admin bilan bog'laning.",
                reply_markup=create_contact_admin_keyboard()
            )
            return
        
        bot_invoice_url = invoice.get("bot_invoice_url")
        
        if not bot_invoice_url:
            await callback_query.message.edit_text(
                "❌ To'lov havolasi yaratishda xatolik yuz berdi.\n\n"
                "Iltimos, boshqa to'lov usulini tanlang yoki admin bilan bog'laning.",
                reply_markup=create_contact_admin_keyboard()
            )
            return
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 To'lov qilish", url=bot_invoice_url)],
            [InlineKeyboardButton(text="👨‍💻 Yordam", url="https://t.me/y0rdam_42")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium")]
        ])
        
        await callback_query.message.edit_text(
            "💎 USDT orqali to'lov qilish uchun quyidagi havolani bosing:\n\n"
            "To'lov miqdori: 3 USDT\n"
            "Eslatma: To'lov muvaffaqiyatli bo'lgandan so'ng, premium statusingiz avtomatik faollashtiriladi.\n\n"
            "Agar muammo yuzaga kelsa, admin bilan bog'laning.",
            reply_markup=keyboard
        )
        
        await record_payment(user_id, 3.0, "crypto", "USDT", "pending", payload)
        
        payment_info = {
            "amount": 3.0,
            "currency": "USDT",
            "method": "Crypto to'lov (USDT)",
            "payment_id": payload,
            "status": "Kutilmoqda"
        }
        
        await notify_admins_about_payment(callback_query.bot, user_id, payment_info)
        
    except Exception as e:
        logger.error(f"Error in crypto payment: {e}")
        await callback_query.message.edit_text(
            "❌ To'lov tizimida xatolik yuz berdi.\n\n"
            f"Xatolik: {str(e)}\n\n"
            "Iltimos, boshqa to'lov usulini tanlang yoki admin bilan bog'laning.",
            reply_markup=create_contact_admin_keyboard()
        )

@router.callback_query(F.data == "crypto_premium_ton_2")
async def process_crypto_premium_ton(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    payload = f"premium_{user_id}_{uuid.uuid4().hex[:8]}"
    
    try:
        await callback_query.answer("To'lov tayyorlanmoqda...")
        
        crypto_pay = CryptoPayAPI()
        invoice = await crypto_pay.create_invoice(
            asset="TON",
            amount="0.6",
            description="Premium obuna - TestBor bot",
            hidden_message="Premium obuna uchun rahmat! Endi testlarni cheksiz yaratishingiz mumkin.",
            paid_btn_name="callback",
            paid_btn_url=f"https://t.me/testbor_bot?start=payment_{payload}",
            payload=payload,
            allow_comments=True,
            allow_anonymous=False,
            expires_in=24 * 3600
        )
        
        if "error" in invoice:
            logger.error(f"Error creating crypto invoice: {invoice['error']}")
            await callback_query.message.edit_text(
                "❌ To'lov tizimida xatolik yuz berdi.\n\n"
                f"Xatolik: {invoice.get('error')}\n\n"
                "Iltimos, boshqa to'lov usulini tanlang yoki admin bilan bog'laning.",
                reply_markup=create_contact_admin_keyboard()
            )
            return
        
        bot_invoice_url = invoice.get("bot_invoice_url")
        
        if not bot_invoice_url:
            await callback_query.message.edit_text(
                "❌ To'lov havolasi yaratishda xatolik yuz berdi.\n\n"
                "Iltimos, boshqa to'lov usulini tanlang yoki admin bilan bog'laning.",
                reply_markup=create_contact_admin_keyboard()
            )
            return
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 To'lov qilish", url=bot_invoice_url)],
            [InlineKeyboardButton(text="👨‍💻 Yordam", url="https://t.me/y0rdam_42")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium")]
        ])
        
        await callback_query.message.edit_text(
            "💎 TON orqali to'lov qilish uchun quyidagi havolani bosing:\n\n"
            "To'lov miqdori: 0.6 TON\n"
            "Eslatma: To'lov muvaffaqiyatli bo'lgandan so'ng, premium statusingiz avtomatik faollashtiriladi.\n\n"
            "Agar muammo yuzaga kelsa, admin bilan bog'laning.",
            reply_markup=keyboard
        )
        
        await record_payment(user_id, 0.6, "crypto", "TON", "pending", payload)
        
        payment_info = {
            "amount": 0.6,
            "currency": "TON",
            "method": "Crypto to'lov (TON)",
            "payment_id": payload,
            "status": "Kutilmoqda"
        }
        
        await notify_admins_about_payment(callback_query.bot, user_id, payment_info)
        
    except Exception as e:
        logger.error(f"Error in crypto payment: {e}")
        await callback_query.message.edit_text(
            "❌ To'lov tizimida xatolik yuz berdi.\n\n"
            f"Xatolik: {str(e)}\n\n"
            "Iltimos, boshqa to'lov usulini tanlang yoki admin bilan bog'laning.",
            reply_markup=create_contact_admin_keyboard()
        )

@router.callback_query(F.data == "buy_premium_payment")
async def process_buy_premium_payment(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "💳 To'lov variantini tanlang:\n\n"
        "• 💫 Premium: 20,000 so'm - cheksiz testlar va 100 ta savolga ruxsat\n"
        "• 🔥 Premium + 10 yulduz: 25,000 so'm - cheksiz testlar, 100 ta savolga ruxsat va 10 bonus yulduz\n\n"
        "⚠️ Agar to'lov bilan muammo bo'lsa, admin bilan bog'laning\n"
        "To'lov qilish uchun variantni tanlang:",
        reply_markup=create_payment_options_keyboard()
    )

@router.callback_query(F.data == "pay_premium_20000")
async def process_pay_premium_standard(callback_query: CallbackQuery):
    if not PAYMENT_PROVIDER_TOKEN or PAYMENT_PROVIDER_TOKEN.startswith("None"):
        await callback_query.message.edit_text(
            "⚠️ To'lov tizimi hozircha mavjud emas.\n\n"
            "Iltimos, yulduzlar orqali xarid qiling yoki admin bilan bog'laning.",
            reply_markup=create_contact_admin_keyboard()
        )
        return

    try:
        await callback_query.answer("To'lov tayyorlanmoqda...")
        
        await callback_query.bot.send_invoice(
            chat_id=callback_query.from_user.id,
            title="Premium obuna",
            description="Cheksiz testlar va 100 savolga ruxsat",
            payload="premium_standard",
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency="UZS",
            prices=get_premium_prices(),
            start_parameter="premium_payment"
        )
        
        await record_payment(
            callback_query.from_user.id, 
            20000, 
            "telegram", 
            "UZS", 
            "pending", 
            f"telegram_premium_{callback_query.from_user.id}_{uuid.uuid4().hex[:8]}"
        )
        
    except Exception as e:
        logger.error(f"Error sending invoice: {e}")
        await callback_query.message.edit_text(
            "❌ To'lov tizimida xatolik yuz berdi.\n\n"
            "Iltimos, boshqa to'lov usulini tanlang yoki admin bilan bog'laning.",
            reply_markup=create_contact_admin_keyboard()
        )

@router.callback_query(F.data == "pay_premium_25000")
async def process_pay_premium_plus(callback_query: CallbackQuery):
    if not PAYMENT_PROVIDER_TOKEN or PAYMENT_PROVIDER_TOKEN.startswith("None"):
        await callback_query.message.edit_text(
            "⚠️ To'lov tizimi hozircha mavjud emas.\n\n"
            "Iltimos, yulduzlar orqali xarid qiling yoki admin bilan bog'laning.",
            reply_markup=create_contact_admin_keyboard()
        )
        return

    try:
        await callback_query.answer("To'lov tayyorlanmoqda...")
        
        await callback_query.bot.send_invoice(
            chat_id=callback_query.from_user.id,
            title="Premium obuna + 10 yulduz",
            description="Cheksiz testlar, 100 savolga ruxsat va 10 bonus yulduz",
            payload="premium_plus",
            provider_token=PAYMENT_PROVIDER_TOKEN,
            currency="UZS",
            prices=get_premium_plus_prices(),
            start_parameter="premium_plus_payment"
        )
        
        await record_payment(
            callback_query.from_user.id, 
            25000, 
            "telegram", 
            "UZS", 
            "pending", 
            f"telegram_premium_plus_{callback_query.from_user.id}_{uuid.uuid4().hex[:8]}"
        )
        
    except Exception as e:
        logger.error(f"Error sending invoice: {e}")
        await callback_query.message.edit_text(
            "❌ To'lov tizimida xatolik yuz berdi.\n\n"
            "Iltimos, boshqa to'lov usulini tanlang yoki admin bilan bog'laning.",
            reply_markup=create_contact_admin_keyboard()
        )

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

async def notify_admins_about_payment(bot, user_id, payment_info):
    config = load_config()
    user = await get_user(user_id)
    username = user[1] if user else "Noma'lum"
    full_name = user[2] if user else "Noma'lum"
    
    notification_text = (
        f"💰 Yangi to'lov qabul qilindi!\n\n"
        f"👤 Foydalanuvchi: {full_name} (@{username})\n"
        f"🆔 ID: {user_id}\n"
        f"💵 Miqdor: {payment_info['amount']} {payment_info['currency']}\n"
        f"💳 To'lov usuli: {payment_info['method']}\n"
        f"🕒 Sana: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"🔑 To'lov ID: {payment_info['payment_id']}\n\n"
        f"✅ Status: {payment_info['status']}"
    )
    
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, notification_text)
        except Exception as e:
            logger.error(f"Error sending payment notification to admin {admin_id}: {e}")

@router.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    user_id = message.from_user.id
    
    payment_id = f"telegram_{payment.invoice_payload}_{user_id}_{uuid.uuid4().hex[:8]}"
    
    await set_premium_status(user_id, True)
    await update_payment_status(payment_id, "completed")
    
    payment_info = {
        "amount": payment.total_amount / 100,
        "currency": payment.currency,
        "method": "Telegram to'lov",
        "payment_id": payment_id,
        "status": "Muvaffaqiyatli"
    }
    
    await notify_admins_about_payment(message.bot, user_id, payment_info)
    
    if payment.invoice_payload == "premium_plus":
        await add_user_stars(user_id, 10)
        await message.answer(
            "🎉 Tabriklaymiz! Premium obuna muvaffaqiyatli faollashtirildi!\n\n"
            "• Cheksiz testlar yaratish imkoniyatiga ega bo'ldingiz\n"
            "• Har bir testda 100 tagacha savol yaratish mumkin\n"
            "• 10 ta bonus yulduz qo'shildi\n\n"
            "✅ To'lovingiz uchun rahmat!",
            reply_markup=create_main_keyboard()
        )
    else:
        await message.answer(
            "🎉 Tabriklaymiz! Premium obuna muvaffaqiyatli faollashtirildi!\n\n"
            "• Cheksiz testlar yaratish imkoniyatiga ega bo'ldingiz\n"
            "• Har bir testda 100 tagacha savol yaratish mumkin\n\n"
            "✅ To'lovingiz uchun rahmat!",
            reply_markup=create_main_keyboard()
        )

@router.callback_query(F.data == "buy_premium_stars")
async def process_buy_premium_stars(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    stars = await get_user_stars(user_id) or 0
    stars_cost = 100
    stars_discount = 10
    discounted_cost = stars_cost - stars_discount
    
    if stars < discounted_cost:
        await callback_query.message.edit_text(
            f"⚠️ Yetarli yulduzlar yo'q!\n\n"
            f"Sizga yana {discounted_cost - stars} yulduz kerak. Testlar yaratib yulduzlar yig'ing.\n"
            f"Hozirgi yulduzlaringiz: {stars} ⭐️\n\n"
            f"Premium olish uchun kerak: {discounted_cost} yulduz\n\n"
            f"Yoki boshqa to'lov usullaridan foydalaning:",
            reply_markup=create_premium_keyboard()
        )
        return
        
    success, result_message = await spend_stars_for_premium(user_id, discounted_cost)
    
    if success:
        await callback_query.message.edit_text(
            "🎉 Tabriklaymiz! Siz premium imkoniyatlardan foydalanishingiz mumkin.\n\n"
            "• Har bir testda 100 tagacha savol yaratish\n"
            "• Cheksiz miqdorda testlar yaratish\n"
            "• Yuqori sifatli testlar\n"
            "• Ustuvor yordam\n\n"
            f"Bepul testlar limitingiz olib tashlandi. Endi istagan miqdorda test yaratasiz!\n"
            f"✨ Sotib olganingiz uchun rahmat! {discounted_cost} yulduz sarflandi, {stars - discounted_cost} yulduz qoldi.",
            reply_markup=create_main_keyboard()
        )
    else:
        await callback_query.message.edit_text(
            f"❌ Xatolik: {result_message}\n\n"
            "Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning.",
            reply_markup=create_contact_admin_keyboard()
        )

@router.callback_query(F.data == "contact_admin")
async def process_contact_admin(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "👨‍💻 Admin bilan bog'lanish:\n\n"
        "• To'lov bilan muammolar uchun\n"
        "• Bot ishlashida xatoliklar bo'lsa\n"
        "• Yangi funksiya bo'yicha takliflar bo'lsa\n\n"
        "Admin: @yordam_42\n\n"
        "Hozirgacha yuborilgan barcha xabarlaringiz albatta ko'rib chiqiladi!",
        reply_markup=create_contact_admin_keyboard()
    )

@router.callback_query(F.data == "help")
async def process_help(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "ℹ️ Yordam: Bu bot turli fanlar bo'yicha test yaratishda yordam beradi.\n\n"
        "• Test yaratish uchun 'Test yaratish' tugmasini bosing\n"
        "• Oddiy foydalanuvchilar har bir testda 30 tagacha savol yarata oladi\n"
        "• Premium foydalanuvchilar cheksiz testlar va har bir testda 100 tagacha savol yarata oladi\n"
        "• Testlar standart Word (.docx) formatida yaratilib, uni qurilmangizda ochishingiz mumkin\n"
        "• Premium olish uchun tugmalar bo'limiga o'ting\n\n"
        "Savollaringiz bo'lsa, admin bilan bog'laning: @yordam_42",
        reply_markup=create_back_keyboard()
    )

@router.callback_query(F.data == "edit_test")
async def process_edit_test(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    
    await callback_query.message.edit_text(
        "✏️ Test tahrirlash\n\n"
        "Bu funksiya tez orada qo'shiladi. Hozirda yangi test yaratish orqali o'zingizga mos testni olishingiz mumkin.\n\n"
        "Agar test formatida muammolarga duch kelsangiz, admin bilan bog'laning.",
        reply_markup=create_back_keyboard()
    )

@router.callback_query(F.data == "regenerate_test")
async def process_regenerate_test(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    
    tests = await get_user_tests(user_id, limit=1)
    
    if not tests:
        await callback_query.message.edit_text(
            "❌ Siz hali hech qanday test yaratmagansiz.",
            reply_markup=create_back_keyboard()
        )
        return
    
    test = tests[0]
    subject = test[0]
    questions_count = test[1]
    
    await state.update_data(subject=subject, questions_count=questions_count, regenerate=True)
    
    await callback_query.message.edit_text(
        f"🔄 Testni qayta yaratish\n\n"
        f"Fan: {subject}\n"
        f"Savol soni: {questions_count}\n\n"
        f"❓ Test uchun qo'shimcha tavsif kiriting (ixtiyoriy):",
        reply_markup=create_skip_keyboard()
    )
    
    await state.set_state(TestGeneration.waiting_for_description)

@router.callback_query(F.data == "change_format")
async def process_change_format(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    await callback_query.message.edit_text(
        "📊 Test formati\n\n"
        "Bu funksiya tez orada qo'shiladi. Hozirda testlar standart formatda taqdim etiladi.\n\n"
        "Agarda maxsus format kerak bo'lsa, admin bilan bog'laning: @yordam_42",
        reply_markup=create_back_keyboard()
    )

@router.callback_query(F.data == "profile")
async def process_profile(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await callback_query.answer("❌ Profil ma'lumotlari topilmadi")
        return
        
    stars = await get_user_stars(user_id) or 0
    tests = await get_user_tests(user_id)
    total_tests = len(tests) if tests else 0
    
    status = "💎 Premium" if user[4] == 1 else "🔹 Oddiy"
    test_limit = "♾️ Cheksiz" if user[4] == 1 else f"📊 {user[5]} ta"
    
    profile_text = (
        f"👤 Profil\n\n"
        f"• Ism: {user[2]}\n"
        f"• Username: @{user[1]}\n"
        f"• Status: {status}\n"
        f"• Test limiti: {test_limit}\n"
        f"• Yaratilgan testlar: {total_tests} ta\n"
        f"• Yulduzlar: {stars} ⭐️\n"
        f"• Ro'yxatdan o'tgan sana: {user[3].strftime('%Y-%m-%d')}"
    )
    
    await callback_query.message.edit_text(
        profile_text,
        reply_markup=create_main_keyboard()
    )

@router.callback_query(F.data == "my_tests")
async def process_my_tests(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    tests = await get_user_tests(user_id)
    
    if not tests:
        await callback_query.message.edit_text(
            "📝 Siz hali hech qanday test yaratmagansiz.",
            reply_markup=create_back_keyboard("back_to_main")
        )
        return
        
    text = "📚 Yaratilgan testlar:\n\n"
    for i, test in enumerate(tests, 1):
        text += f"{i}. {test[0]}\n"
        text += f"   • Savollar soni: {test[1]} ta\n"
        text += f"   • Yaratilgan sana: {test[2].strftime('%Y-%m-%d')}\n\n"
    
    await callback_query.message.edit_text(
        text,
        reply_markup=create_back_keyboard("back_to_main")
    )