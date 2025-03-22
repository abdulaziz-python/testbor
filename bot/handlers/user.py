from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction  
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
import asyncio
import math


from bot.keyboards.inline import (
    create_main_keyboard, create_subscription_keyboard,
    create_skip_keyboard, create_back_keyboard,
    create_premium_keyboard, create_pagination_keyboard
)
from bot.utils.database import (
    register_user, get_user, update_test_count,
    save_test_info, get_user_tests
)
from bot.utils.document import generate_test_document
from bot.utils.subscription import check_subscription
from bot.utils.logger import get_logger
from config.config import load_config, ConfigError

logger = get_logger(__name__)
router = Router()

class TestGeneration(StatesGroup):
    waiting_for_subject = State()
    waiting_for_description = State()
    waiting_for_questions_count = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username
        full_name = message.from_user.full_name

        await register_user(user_id, username, full_name)

        config = load_config()
        is_subscribed = await check_subscription(user_id, config.required_channels)

        if is_subscribed:
            await message.answer(
                f"👋 Salom, {full_name}! Testbor botiga xush kelibsiz. Men turli fanlar bo'yicha test yaratishda yordam beraman.\nNima qilishni xohlaysiz?",
                reply_markup=create_main_keyboard()
            )
        else:
            await message.answer(
                f"👋 Salom, {full_name}! Botdan foydalanish uchun quyidagi kanallarga obuna bo'lishingiz kerak:",
                reply_markup=create_subscription_keyboard(config.required_channels)
            )
    except aiogram.exceptions.TelegramForbiddenError:
        logger.warning(f"User {user_id} has blocked the bot")
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(
            "Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring yoki admin bilan bog'laning: @y0rdam42"
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Yordam: Bu bot turli fanlar bo'yicha test yaratishda yordam beradi.\n"
        "• Test yaratish uchun 'Test yaratish' tugmasini bosing\n"
        "• Oddiy foydalanuvchilar har bir testda 30 tagacha savol yarata oladi\n"
        "• Premium foydalanuvchilar cheksiz testlar va har bir testda 100 tagacha savol yarata oladi\n"
        "Savollaringiz bo'lsa, admin bilan bog'laning: @y0rdam42",
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
        tests_generated = user[6]
        test_limit = user[5]
        is_premium = user[4]

        if tests_generated >= test_limit and not is_premium:
            await callback_query.answer(
                "❌ Siz bepul test limitiga yetdingiz. Premium obunaga o'ting.",
                show_alert=True
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

        await message.answer("⏳")
        await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

        if questions_count > 20:
            chunks = []
            chunk_size = 20
            remaining = questions_count

            while remaining > 0:
                current_chunk = min(chunk_size, remaining)
                chunk_test = await generate_test_document(subject, description, current_chunk)
                if chunk_test:
                    chunks.append(chunk_test)
                remaining -= current_chunk
                
                if remaining > 0:
                    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

            await update_test_count(user_id)
            await save_test_info(user_id, subject, description, questions_count)

            for i, chunk in enumerate(chunks, 1):
                await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_DOCUMENT)
                
                filename = f"{subject}_test_part{i}.docx" if len(chunks) > 1 else f"{subject}_test.docx"
                caption = (
                    f"✅ {subject} bo'yicha test - {i}-qism\n"
                    f"❗️ Test savollarida imlo xatolari yoki uslubiy nomuvofiqliklar bo'lishi mumkin."
                ) if len(chunks) > 1 else (
                    f"✅ {subject} bo'yicha test\n"
                    f"❗️ Test savollarida imlo xatolari yoki uslubiy nomuvofiqliklar bo'lishi mumkin."
                )

                await message.answer_document(
                    document=BufferedInputFile(
                        chunk.getvalue(),
                        filename=filename
                    ),
                    caption=caption
                )

            if len(chunks) > 1:
                await message.answer(
                    f"✅ Test {len(chunks)} qismga bo'lib yuborildi.\n"
                    f"Umumiy savollar soni: {questions_count}",
                    reply_markup=create_main_keyboard()
                )
            
        else:
            test_file = await generate_test_document(subject, description, questions_count)

            if test_file:
                await update_test_count(user_id)
                await save_test_info(user_id, subject, description, questions_count)

                await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_DOCUMENT)
                
                await message.answer_document(
                    document=BufferedInputFile(
                        test_file.getvalue(),
                        filename=f"{subject}_test.docx"
                    ),
                    caption=(
                        f"✅ {subject} bo'yicha test\n"
                        f"❗️ Test savollarida imlo xatolari yoki uslubiy nomuvofiqliklar bo'lishi mumkin."
                    )
                )

        await message.answer(
            "Yana test yaratishni xohlaysizmi?",
            reply_markup=create_main_keyboard()
        )

    except ValueError:
        await message.answer("❌ Iltimos, to'g'ri son kiriting.")
    except Exception as e:
        logger.error(f"Error generating test: {e}")
        await message.answer(
            "❌ Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
            reply_markup=create_main_keyboard()
        )
    finally:
        await state.clear()



@router.callback_query(F.data == "premium")
async def process_premium(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "* Nimaga premium olishim kerak? *\n\n"
        "Premium Atiga 20 ming so'm. Bu pulni to'lashni hech kim xohlamaydi, chunki bizning xalq internetda har bir narsani tekinga hal qilishni istaydi. Lekin har bir loyiha katta mehnat talab qiladi va ayniqsa, raqamli dunyoda bu mehnatni to‘g‘ri rag‘batlantirish muhim. 💡\n\nBu pul evaziga siz cheksiz test yaratish imkoniyatiga ega bo‘lasiz. ✅\nAgar o‘qituvchi bo‘lsangiz – vaqtingizni tejaysiz. ⏳\nAgar o‘quvchi bo‘lsangiz – istalgan vaqtda, istalgan fan uchun test yaratishingiz mumkin. 📚\n\nAtigi bir mahal ovqat 🍔 yoki keraksiz narsaga sarflanadigan pulni tejab, premiumni bemalol xarid qilishingiz mumkin.\n\n 'ChatGPT yoki boshqa tekin xizmatlar bor' deb o‘ylashingiz mumkin, lekin hech biri bitta bosishda bu qadar ko‘p test yaratib, tayyor Word shaklida taqdim eta olmaydi! 📄\n\nHozircha premium faqat cheksiz test yaratish imkoniyatini beradi, ammo kelajakda yanada samarali va natijali testlar qo‘shiladi. 🚀\n\nO‘ylaymanki, meni to‘g‘ri tushundingiz va premiumni sotib olasiz. 😉"
        "💰 Premium imkoniyatlari:\n\n"
        "• 🧪Har bir testda 💯 tagacha savol yaratish\n"
        "• ✨Cheksiz miqdorda testlar yaratish\n"
        "• 🌟20 ming so'm evaziga umrbodga premium"
        "• 🆘Ustuvor yordam\n\n"
        "Premium obunaga o'tish uchun admin bilan bog'laning: @y0rdam42",
        reply_markup=create_premium_keyboard()
    )

@router.callback_query(F.data == "help")
async def process_help(callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "ℹ️ Yordam:\n\n"
        "Bu bot turli fanlar bo'yicha test yaratishda yordam beradi.\n\n"
        "• Test yaratish uchun 'Test yaratish' tugmasini bosing\n"
        "• Oddiy foydalanuvchilar har bir testda 30 tagacha savol yarata oladi\n"
        "• Premium foydalanuvchilar cheksiz testlar va har bir testda 100 tagacha savol yarata oladi\n\n"
        "Savollaringiz bo'lsa, admin bilan bog'laning: @y0rdam42",
        reply_markup=create_back_keyboard()
    )

@router.callback_query(F.data == "profile")
async def process_profile(callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        user = await get_user(user_id)

        if user:
            tests_generated = user[6] or 0
            test_limit = user[5] or 30
            is_premium = user[4] == 1
            username = user[1] if user[1] else "O'rnatilmagan"

            status = "💎 Premium" if is_premium else "🔹 Oddiy"
            limit_text = "Cheksiz" if is_premium else f"{tests_generated}/{test_limit}"

            await callback_query.message.edit_text(
                f"👤 Sizning profilingiz:\n\n"
                f"• Ism: {user[2]}\n"
                f"• Foydalanuvchi nomi: @{username}\n"
                f"• Status: {status}\n"
                f"• Yaratilgan testlar: {limit_text}\n"
                f"• Ro'yxatdan o'tgan sana: {user[3]}",
                reply_markup=create_back_keyboard()
            )
        else:
            await callback_query.answer(
                "❌ Profilni yuklashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
                show_alert=True
            )
    except Exception as e:
        logger.error(f"Error in profile view: {e}")
        await callback_query.answer(
            "Xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
            show_alert=True
        )


@router.callback_query(F.data == "my_tests")
async def process_my_tests(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id

    tests = await get_user_tests(user_id)

    if tests:
        text = "📊 Sizning so'nggi testlaringiz:\n\n"
        for i, test in enumerate(tests, 1):
            subject = test[0]
            questions = test[1]
            date = test[2]
            text += f"{i}. {subject} ({questions} ta savol) - {date}\n"

        await callback_query.message.edit_text(
            text,
            reply_markup=create_back_keyboard()
        )
    else:
        await callback_query.message.edit_text(
            "Siz hali hech qanday test yaratmagansiz.",
            reply_markup=create_back_keyboard()
        )

@router.callback_query(F.data == "back_to_main")
async def process_back_to_main(callback_query: CallbackQuery):
    try:
        await callback_query.message.edit_text(
            "Nima qilishni xohlaysiz?",
            reply_markup=create_main_keyboard()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback_query.answer("Siz asosiy menyudasiz")
        else:
            logger.error(f"Error in back_to_main: {e}")
            await callback_query.answer("Xatolik yuz berdi")


@router.callback_query(F.data.startswith("page:"))
async def process_pagination(callback_query: CallbackQuery, state: FSMContext):
    page = int(callback_query.data.split(":", 1)[1])

    await callback_query.answer(f"{page}-sahifa tanlandi")



