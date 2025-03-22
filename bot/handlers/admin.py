from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import asyncio

from bot.keyboards.inline import (
    create_admin_keyboard, create_back_keyboard,
    create_broadcast_confirmation_keyboard, create_premium_status_keyboard
)
from bot.utils.database import (
    get_user, update_user_limit, get_all_users,
    get_user_stats, get_top_users, set_premium_status
)
from bot.utils.logger import get_logger
from config.config import load_config

logger = get_logger(__name__)
router = Router()
config = load_config()

class AdminStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_new_limit = State()
    waiting_for_broadcast_message = State()
    waiting_for_premium_user_id = State()
    broadcast_media = State()
    broadcast_text = State()
    broadcast_entities = State()

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    config = load_config()

    if message.from_user.id in config.admin_ids:
        await message.answer(
            "👑 Admin paneli\n\nVariantni tanlang:",
            reply_markup=create_admin_keyboard()
        )
    else:
        await message.answer("Sizda admin paneliga kirish huquqi yo'q.")

@router.callback_query(F.data == "admin_users")
async def process_admin_users(callback_query: CallbackQuery):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("Sizda admin paneliga kirish huquqi yo'q.")
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
        await callback_query.answer("Sizda admin paneliga kirish huquqi yo'q.")
        return

    await callback_query.message.edit_text(
        "Test limitini o'zgartirish uchun foydalanuvchi ID raqamini kiriting:"
    )

    await state.set_state(AdminStates.waiting_for_user_id)

@router.message(AdminStates.waiting_for_user_id)
async def process_admin_user_id(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("Sizda admin paneliga kirish huquqi yo'q.")
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
            await message.answer("Foydalanuvchi topilmadi. Iltimos, qayta urinib ko'ring yoki admin paneliga qayting.")

    except ValueError:
        await message.answer("Iltimos, to'g'ri ID raqamini kiriting.")

@router.message(AdminStates.waiting_for_new_limit)
async def process_admin_new_limit(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("Sizda admin paneliga kirish huquqi yo'q.")
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
            reply_markup=create_admin_keyboard()
        )

        await state.clear()

    except ValueError:
        await message.answer("Iltimos, to'g'ri son kiriting.")

@router.callback_query(F.data == "admin_broadcast")
async def process_admin_broadcast(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("Sizda admin paneliga kirish huquqi yo'q.")
        return

    await callback_query.message.edit_text(
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni kiriting:"
    )

    await state.set_state(AdminStates.waiting_for_broadcast_message)

@router.message(AdminStates.waiting_for_broadcast_message)
async def process_admin_broadcast_message(message: Message, state: FSMContext):
    if message.from_user.id not in config.admin_ids:
        await message.answer("Sizda admin paneliga kirish huquqi yo'q.")
        await state.clear()
        return

    broadcast_data = {
        "text": message.text or message.caption or "",
        "entities": message.entities or message.caption_entities,
        "photo_id": None,
        "video_id": None,
        "animation_id": None,
        "document_id": None,
    }

    if message.photo:
        broadcast_data["photo_id"] = message.photo[-1].file_id
    elif message.video:
        broadcast_data["video_id"] = message.video.file_id
    elif message.animation:
        broadcast_data["animation_id"] = message.animation.file_id
    elif message.document:
        broadcast_data["document_id"] = message.document.file_id

    await state.update_data(broadcast_data=broadcast_data)
    
    users = await get_all_users()
    preview_text = broadcast_data["text"][:200] + "..." if len(broadcast_data["text"]) > 200 else broadcast_data["text"]

    message_text = f"{message.message_id}:{preview_text}"

    preview_message = f"Siz ushbu xabarni {len(users)} ta foydalanuvchiga yubormoqchisiz:\n\n{preview_text}"
    if any([broadcast_data["photo_id"], broadcast_data["video_id"], 
            broadcast_data["animation_id"], broadcast_data["document_id"]]):
        preview_message += "\n\n(Media bilan birga)"

    await message.answer(
        preview_message,
        reply_markup=create_broadcast_confirmation_keyboard(message_text)
    )

@router.callback_query(F.data.startswith("confirm_broadcast:"))
async def process_confirm_broadcast(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("Sizda admin paneliga kirish huquqi yo'q.")
        return

    data = await state.get_data()
    broadcast_data = data.get("broadcast_data")
    
    if not broadcast_data:
        await callback_query.answer("Xabar topilmadi.")
        return

    users = await get_all_users()
    
    if not users:
        await callback_query.message.edit_text(
            "❌ Foydalanuvchilar topilmadi. Xabar yuborib bo'lmaydi.",
            reply_markup=create_back_keyboard("back_to_admin")
        )
        return

    status_message = await callback_query.message.edit_text(
        f"📢 Xabar yuborilmoqda...\n"
        f"Umumiy: {len(users)}\n"
        f"Yuborildi: 0\n"
        f"Jarayon: 0/{len(users)}"
    )

    success_count = 0
    blocked_count = 0
    failed_count = 0

    for i, user_row in enumerate(users, 1):
        try:
            user_id = user_row[0]
            
            try:
                if broadcast_data["photo_id"]:
                    await callback_query.bot.send_photo(
                        chat_id=user_id,
                        photo=broadcast_data["photo_id"],
                        caption=broadcast_data["text"],
                        caption_entities=broadcast_data["entities"]
                    )
                elif broadcast_data["video_id"]:
                    await callback_query.bot.send_video(
                        chat_id=user_id,
                        video=broadcast_data["video_id"],
                        caption=broadcast_data["text"],
                        caption_entities=broadcast_data["entities"]
                    )
                elif broadcast_data["animation_id"]:
                    await callback_query.bot.send_animation(
                        chat_id=user_id,
                        animation=broadcast_data["animation_id"],
                        caption=broadcast_data["text"],
                        caption_entities=broadcast_data["entities"]
                    )
                elif broadcast_data["document_id"]:
                    await callback_query.bot.send_document(
                        chat_id=user_id,
                        document=broadcast_data["document_id"],
                        caption=broadcast_data["text"],
                        caption_entities=broadcast_data["entities"]
                    )
                else:
                    await callback_query.bot.send_message(
                        chat_id=user_id,
                        text=broadcast_data["text"],
                        entities=broadcast_data["entities"]
                    )
                
                success_count += 1
                
            except TelegramForbiddenError:
                blocked_count += 1
                logger.warning(f"User {user_id} has blocked the bot")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error sending broadcast to user {user_id}: {e}")

            if i % 10 == 0:
                await status_message.edit_text(
                    f"📢 Xabar yuborilmoqda...\n"
                    f"Umumiy: {len(users)}\n"
                    f"Yuborildi: {success_count}\n"
                    f"Bloklangan: {blocked_count}\n"
                    f"Xatolik: {failed_count}\n"
                    f"Jarayon: {i}/{len(users)}"
                )

            await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"Unexpected error with user {user_id}: {e}")
            failed_count += 1

    await status_message.edit_text(
        f"✅ Xabar yuborish yakunlandi!\n\n"
        f"📊 Statistika:\n"
        f"• Umumiy: {len(users)}\n"
        f"• Muvaffaqiyatli: {success_count}\n"
        f"• Bloklangan: {blocked_count}\n"
        f"• Xatolik: {failed_count}",
        reply_markup=create_back_keyboard("back_to_admin")
    )

    await state.clear()




@router.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback_query: CallbackQuery):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("Sizda admin paneliga kirish huquqi yo'q.")
        return

    stats = await get_user_stats()

    await callback_query.message.edit_text(
        f"📊 Bot statistikasi:\n\n"
        f"• Jami foydalanuvchilar: {stats['total_users']}\n"
        f"• Premium foydalanuvchilar: {stats['premium_users']}\n"
        f"• Oddiy foydalanuvchilar: {stats['free_users']}\n"
        f"• Jami yaratilgan testlar: {stats['total_tests']}\n"
        f"• Bugun yaratilgan testlar: {stats['tests_today']}\n"
        f"• Bugun faol foydalanuvchilar: {stats['active_users_today']}",
        reply_markup=create_back_keyboard("back_to_admin")
    )

@router.callback_query(F.data == "admin_set_premium")
async def process_admin_set_premium(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("Sizda admin paneliga kirish huquqi yo'q.")
        return

    await callback_query.message.edit_text(
        "Premium statusini o'zgartirish uchun foydalanuvchi ID raqamini kiriting:"
    )

    await state.set_state(AdminStates.waiting_for_premium_user_id)

@router.message(AdminStates.waiting_for_premium_user_id)
async def process_admin_premium_user_id(message: Message, state: FSMContext):
    config = load_config()

    if message.from_user.id not in config.admin_ids:
        await message.answer("Sizda admin paneliga kirish huquqi yo'q.")
        await state.clear()
        return

    try:
        user_id = int(message.text)

        user = await get_user(user_id)

        if user:
            is_premium = user[4] == 1
            status = "Premium" if is_premium else "Oddiy"

            await state.update_data(premium_user_id=user_id)

            await message.answer(
                f"{user[2]} (ID: {user_id}) foydalanuvchisi hozirda {status} statusida.\n\nYangi statusni tanlang:",
                reply_markup=create_premium_status_keyboard()
            )
        else:
            await message.answer("Foydalanuvchi topilmadi. Iltimos, qayta urinib ko'ring yoki admin paneliga qayting.")

    except ValueError:
        await message.answer("Iltimos, to'g'ri ID raqamini kiriting.")

@router.callback_query(F.data.startswith("set_premium:"))
async def process_set_premium(callback_query: CallbackQuery, state: FSMContext):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("Sizda admin paneliga kirish huquqi yo'q.")
        return

    premium_value = int(callback_query.data.split(":", 1)[1])
    data = await state.get_data()
    user_id = data.get("premium_user_id")

    if not user_id:
        await callback_query.answer("Xato: Foydalanuvchi ID raqami topilmadi.")
        return

    success = await set_premium_status(user_id, premium_value == 1)

    if success:
        status = "Premium" if premium_value == 1 else "Oddiy"
        await callback_query.message.edit_text(
            f"✅ {user_id} ID raqamli foydalanuvchi endi {status} statusiga ega.",
            reply_markup=create_back_keyboard("back_to_admin")
        )
        # Notify the user about their new premium status
        bot = callback_query.bot
        await bot.send_message(chat_id=user_id, text="🎉 Siz endi Premium foydalanuvchisiz!")

    else:
        await callback_query.message.edit_text(
            f"❌ {user_id} ID raqamli foydalanuvchi uchun premium statusini o'zgartirishda xatolik yuz berdi.",
            reply_markup=create_back_keyboard("back_to_admin")
        )

    await state.clear()

@router.callback_query(F.data == "back_to_admin")
async def process_back_to_admin(callback_query: CallbackQuery):
    config = load_config()

    if callback_query.from_user.id not in config.admin_ids:
        await callback_query.answer("Sizda admin paneliga kirish huquqi yo'q.")
        return

    await callback_query.message.edit_text(
        "👑 Admin paneli\n\nVariantni tanlang:",
        reply_markup=create_admin_keyboard()
    )


