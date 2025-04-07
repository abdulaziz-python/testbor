from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import asyncio
import uuid
import datetime

from bot.keyboards.inline import (
    create_back_keyboard,
    create_broadcast_confirmation_keyboard, create_premium_status_keyboard,
    create_admin_panel_keyboard, create_admin_status_keyboard
)
from bot.utils.database import (
    get_user, update_user_limit, get_all_users,
    get_user_stats, get_top_users, set_premium_status,
    save_promo_code, set_admin_status, check_is_admin
)
from bot.utils.logger import get_logger
from bot.utils.crypto_pay import CryptoPayAPI, test_crypto_pay
from config.config import load_config

logger = get_logger(__name__)
router = Router()
config = load_config()

class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_new_limit = State()
    waiting_for_broadcast_message = State()
    waiting_for_premium_user_id = State()
    waiting_for_admin_user_id = State()
    waiting_for_promo_duration = State()
    waiting_for_promo_count = State()
    broadcast_media = State()
    broadcast_text = State()
    broadcast_entities = State()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    config = load_config()
    
    if message.from_user.id in config.admin_ids:
        await message.answer(
            "👑 Admin paneli\n\nVariantni tanlang:",
            reply_markup=create_admin_panel_keyboard()
        )
    else:
        await message.answer("Sizda admin paneliga kirish huquqi yo'q.")

@router.callback_query(F.data == "admin_users")
async def process_admin_users(callback_query: CallbackQuery):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    users = await get_top_users(10)

    if users:
        text = "👥 Foydalanuvchilar ro'yxati (Top 10):\n\n"
        for user in users:
            status = "💎 Premium" if user[3] == 1 else "🔹 Oddiy"
            text += f"ID: {user[0]}\nIsm: {user[2]}\nUsername: @{user[1]}\nStatus: {status}\nTestlar: {user[4]}\n\n"
    else:
        text = "Foydalanuvchilar topilmadi."

    await callback_query.message.edit_text(
        text,
        reply_markup=create_back_keyboard("back_to_admin")
    )

@router.callback_query(F.data == "admin_set_limit")
async def process_admin_set_limit(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    await callback_query.message.edit_text(
        "Test limitini o'zgartirish uchun foydalanuvchi ID raqamini kiriting:"
    )

    await state.set_state(AdminStates.waiting_for_user_id)

@router.message(AdminStates.waiting_for_user_id)
async def process_admin_user_id(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ Sizda admin huquqlari yo'q")
        await state.clear()
        return

    try:
        user_id = int(message.text)

        user = await get_user(user_id)

        if user:
            await state.update_data(target_user_id=user_id)
            await message.answer(f"{user[2]} (ID: {user_id}) foydalanuvchisi uchun yangi test limitini kiriting:")
            await state.set_state(AdminStates.waiting_for_new_limit)
        else:
            await message.answer("Foydalanuvchi topilmadi. Iltimos, qayta urinib ko'ring yoki admin paneliga qayting.",
                               reply_markup=create_back_keyboard("back_to_admin"))

    except ValueError:
        await message.answer("Iltimos, to'g'ri ID raqamini kiriting.",
                          reply_markup=create_back_keyboard("back_to_admin"))

@router.message(AdminStates.waiting_for_new_limit)
async def process_admin_new_limit(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ Sizda admin huquqlari yo'q")
        await state.clear()
        return

    try:
        new_limit = int(message.text)

        if new_limit < 0:
            await message.answer("Iltimos, musbat son kiriting.")
            return

        data = await state.get_data()
        target_user_id = data.get("target_user_id")

        await update_user_limit(target_user_id, new_limit)

        await message.answer(
            f"✅ {target_user_id} ID raqamli foydalanuvchi uchun test limiti {new_limit} ga o'zgartirildi.",
            reply_markup=create_admin_panel_keyboard()
        )

        await state.clear()

    except ValueError:
        await message.answer("Iltimos, to'g'ri son kiriting.",
                         reply_markup=create_back_keyboard("back_to_admin"))

@router.callback_query(F.data == "admin_broadcast")
async def process_admin_broadcast(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    await callback_query.message.edit_text(
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni kiriting:"
    )

    await state.set_state(AdminStates.waiting_for_broadcast_message)

@router.message(AdminStates.waiting_for_broadcast_message)
async def process_admin_broadcast_message(message: Message, state: FSMContext):
    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ Sizda admin huquqlari yo'q")
        await state.clear()
        return

    broadcast_data = {
        "text": message.text or message.caption or "",
        "entities": message.entities or message.caption_entities,
        "media": None,
        "media_type": None
    }

    if message.photo:
        broadcast_data["media"] = message.photo[-1].file_id
        broadcast_data["media_type"] = "photo"
    elif message.video:
        broadcast_data["media"] = message.video.file_id
        broadcast_data["media_type"] = "video"
    elif message.animation:
        broadcast_data["media"] = message.animation.file_id
        broadcast_data["media_type"] = "animation"
    elif message.document:
        broadcast_data["media"] = message.document.file_id
        broadcast_data["media_type"] = "document"

    await state.update_data(broadcast_data=broadcast_data)
    
    users = await get_all_users()
    preview_text = broadcast_data["text"][:200] + "..." if len(broadcast_data["text"]) > 200 else broadcast_data["text"]

    preview_message = f"Siz ushbu xabarni {len(users)} ta foydalanuvchiga yubormoqchisiz:\n\n{preview_text}"
    if broadcast_data["media"]:
        preview_message += f"\n\n(Media bilan birga: {broadcast_data['media_type']})"

    await message.answer(
        preview_message,
        reply_markup=create_broadcast_confirmation_keyboard(message.message_id)
    )

@router.callback_query(F.data.startswith("confirm_broadcast:"))
async def process_confirm_broadcast(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    data = await state.get_data()
    broadcast_data = data.get("broadcast_data")
    
    if not broadcast_data:
        await callback_query.answer("Xatolik: Xabar ma'lumotlari topilmadi", show_alert=True)
        return

    await callback_query.message.edit_text("📤 Xabar yuborilmoqda...")
    
    users = await get_all_users()
    total_users = len(users)
    sent_count = 0
    blocked_count = 0
    failed_count = 0

    for user in users:
        try:
            if broadcast_data["media"]:
                if broadcast_data["media_type"] == "photo":
                    await callback_query.bot.send_photo(
                        user[0],
                        broadcast_data["media"],
                        caption=broadcast_data["text"],
                        parse_mode="HTML"
                    )
                elif broadcast_data["media_type"] == "video":
                    await callback_query.bot.send_video(
                        user[0],
                        broadcast_data["media"],
                        caption=broadcast_data["text"],
                        parse_mode="HTML"
                    )
                elif broadcast_data["media_type"] == "animation":
                    await callback_query.bot.send_animation(
                        user[0],
                        broadcast_data["media"],
                        caption=broadcast_data["text"],
                        parse_mode="HTML"
                    )
                elif broadcast_data["media_type"] == "document":
                    await callback_query.bot.send_document(
                        user[0],
                        broadcast_data["media"],
                        caption=broadcast_data["text"],
                        parse_mode="HTML"
                    )
            else:
                await callback_query.bot.send_message(
                    user[0],
                    broadcast_data["text"],
                    parse_mode="HTML"
                )
            sent_count += 1
        except TelegramForbiddenError:
            blocked_count += 1
        except Exception as e:
            logger.error(f"Error sending broadcast to user {user[0]}: {e}")
            failed_count += 1

    status_message = (
        f"📊 Xabar yuborish yakunlandi:\n\n"
        f"✅ Yuborildi: {sent_count}\n"
        f"❌ Bloklangan: {blocked_count}\n"
        f"⚠️ Xatolik: {failed_count}\n"
        f"📝 Jami: {total_users}"
    )

    await callback_query.message.edit_text(
        status_message,
        reply_markup=create_back_keyboard("back_to_admin")
    )
    await state.clear()

@router.callback_query(F.data == "admin_set_premium")
async def process_admin_set_premium(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    await callback_query.message.edit_text(
        "Premium statusini o'zgartirish uchun foydalanuvchi ID raqamini kiriting:"
    )

    await state.set_state(AdminStates.waiting_for_premium_user_id)

@router.message(AdminStates.waiting_for_premium_user_id)
async def process_admin_premium_user_id(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ Sizda admin huquqlari yo'q")
        await state.clear()
        return

    try:
        user_id = int(message.text)
        user = await get_user(user_id)

        if user:
            current_status = "💎 Premium" if user[4] == 1 else "🔹 Oddiy"
            await state.update_data(target_user_id=user_id)
            await message.answer(
                f"Foydalanuvchi: {user[2]} (ID: {user_id})\n"
                f"Joriy status: {current_status}\n\n"
                "Yangi statusni tanlang:",
                reply_markup=create_premium_status_keyboard()
            )
        else:
            await message.answer("Foydalanuvchi topilmadi. Iltimos, qayta urinib ko'ring yoki admin paneliga qayting.",
                               reply_markup=create_back_keyboard("back_to_admin"))

    except ValueError:
        await message.answer("Iltimos, to'g'ri ID raqamini kiriting.",
                          reply_markup=create_back_keyboard("back_to_admin"))

@router.callback_query(F.data.startswith("set_premium:"))
async def process_set_premium(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        await callback_query.answer("Xatolik: Foydalanuvchi ID topilmadi", show_alert=True)
        return

    is_premium = callback_query.data.split(":")[1] == "true"
    success = await set_premium_status(target_user_id, is_premium)

    if success:
        status = "💎 Premium" if is_premium else "🔹 Oddiy"
        await callback_query.message.edit_text(
            f"✅ {target_user_id} ID raqamli foydalanuvchi uchun status {status} ga o'zgartirildi.",
            reply_markup=create_admin_panel_keyboard()
        )
    else:
        await callback_query.message.edit_text(
            "❌ Statusni o'zgartirishda xatolik yuz berdi.",
            reply_markup=create_back_keyboard("back_to_admin")
        )

    await state.clear()

@router.callback_query(F.data == "admin_create_promo")
async def process_admin_create_promo(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    await callback_query.message.edit_text(
        "Promo kod muddatini kiriting (kunlarda):"
    )

    await state.set_state(AdminStates.waiting_for_promo_duration)

@router.message(AdminStates.waiting_for_promo_duration)
async def process_promo_duration(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ Sizda admin huquqlari yo'q")
        await state.clear()
        return

    try:
        duration = int(message.text)
        if duration <= 0:
            await message.answer("Iltimos, musbat son kiriting.")
            return

        await state.update_data(duration=duration)
        await message.answer(
            "Promo kodlar sonini kiriting:"
        )

        await state.set_state(AdminStates.waiting_for_promo_count)

    except ValueError:
        await message.answer("Iltimos, to'g'ri son kiriting.",
                          reply_markup=create_back_keyboard("back_to_admin"))

@router.message(AdminStates.waiting_for_promo_count)
async def process_promo_count(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ Sizda admin huquqlari yo'q")
        await state.clear()
        return

    try:
        count = int(message.text)
        if count <= 0:
            await message.answer("Iltimos, musbat son kiriting.")
            return

        data = await state.get_data()
        duration = data.get("duration")

        promo_codes = []
        for _ in range(count):
            code = str(uuid.uuid4())[:8].upper()
            expiry_date = datetime.datetime.now() + datetime.timedelta(days=duration)
            success = await save_promo_code(code, expiry_date, message.from_user.id)
            
            if success:
                promo_codes.append(code)

        if promo_codes:
            text = "✅ Promo kodlar muvaffaqiyatli yaratildi:\n\n"
            for code in promo_codes:
                text += f"• {code}\n"
            
            text += f"\nMuddati: {duration} kun"
            
            await message.answer(
                text,
                reply_markup=create_admin_panel_keyboard()
            )
        else:
            await message.answer(
                "❌ Promo kodlar yaratishda xatolik yuz berdi.",
                reply_markup=create_back_keyboard("back_to_admin")
            )

        await state.clear()

    except ValueError:
        await message.answer("Iltimos, to'g'ri son kiriting.",
                         reply_markup=create_back_keyboard("back_to_admin"))

@router.callback_query(F.data == "admin_crypto_webhook")
async def process_admin_crypto_webhook(callback_query: CallbackQuery):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    try:
        crypto_pay = CryptoPayAPI(config.crypto_pay_token)
        success = await test_crypto_pay(crypto_pay)

        if success:
            await callback_query.message.edit_text(
                "✅ Crypto Pay webhook muvaffaqiyatli sozlandi.",
                reply_markup=create_admin_panel_keyboard()
            )
        else:
            await callback_query.message.edit_text(
                "❌ Crypto Pay webhook sozlashda xatolik yuz berdi.",
                reply_markup=create_back_keyboard("back_to_admin")
            )

    except Exception as e:
        logger.error(f"Error setting up crypto webhook: {e}")
        await callback_query.message.edit_text(
            "❌ Crypto Pay webhook sozlashda xatolik yuz berdi.",
            reply_markup=create_back_keyboard("back_to_admin")
        )

@router.callback_query(F.data == "back_to_admin")
async def process_back_to_admin(callback_query: CallbackQuery):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    await callback_query.message.edit_text(
        "👑 Admin paneli\n\nVariantni tanlang:",
        reply_markup=create_admin_panel_keyboard()
    )

@router.callback_query(F.data == "admin_set_admin")
async def process_admin_set_admin(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    await callback_query.message.edit_text(
        "Admin huquqini o'zgartirish uchun foydalanuvchi ID raqamini kiriting:"
    )

    await state.set_state(AdminStates.waiting_for_admin_user_id)

@router.message(AdminStates.waiting_for_admin_user_id)
async def process_admin_user_id_for_admin(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("⛔ Sizda admin huquqlari yo'q")
        await state.clear()
        return

    try:
        user_id = int(message.text)
        user = await get_user(user_id)

        if user:
            current_status = "👑 Admin" if await check_is_admin(user_id) else "👤 Oddiy"
            await state.update_data(target_user_id=user_id)
            await message.answer(
                f"Foydalanuvchi: {user[2]} (ID: {user_id})\n"
                f"Joriy status: {current_status}\n\n"
                "Yangi statusni tanlang:",
                reply_markup=create_admin_status_keyboard()
            )
        else:
            await message.answer("Foydalanuvchi topilmadi. Iltimos, qayta urinib ko'ring yoki admin paneliga qayting.",
                               reply_markup=create_back_keyboard("back_to_admin"))

    except ValueError:
        await message.answer("Iltimos, to'g'ri ID raqamini kiriting.",
                          reply_markup=create_back_keyboard("back_to_admin"))

@router.callback_query(F.data.startswith("set_admin:"))
async def process_set_admin(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("⛔ Sizda admin huquqlari yo'q", show_alert=True)
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")

    if not target_user_id:
        await callback_query.answer("Xatolik: Foydalanuvchi ID topilmadi", show_alert=True)
        return

    is_admin = callback_query.data.split(":")[1] == "true"
    success = await set_admin_status(target_user_id, is_admin)

    if success:
        status = "👑 Admin" if is_admin else "👤 Oddiy"
        await callback_query.message.edit_text(
            f"✅ {target_user_id} ID raqamli foydalanuvchi uchun status {status} ga o'zgartirildi.",
            reply_markup=create_admin_panel_keyboard()
        )
    else:
        await callback_query.message.edit_text(
            "❌ Statusni o'zgartirishda xatolik yuz berdi.",
            reply_markup=create_back_keyboard("back_to_admin")
        )

    await state.clear()


