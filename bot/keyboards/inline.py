from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict
import hashlib

def create_subscription_keyboard(required_channels: List[Dict[str, str]]):
    keyboard = []

    for channel in required_channels:
        keyboard.append([
            InlineKeyboardButton(text=f"📢 {channel['title']}", url=f"https://t.me/{channel['id'][1:]}")
        ])

    keyboard.append([
        InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_main_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="📝 Test yaratish", callback_data="generate_test"),
            InlineKeyboardButton(text="💰 Premium", callback_data="premium")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help"),
            InlineKeyboardButton(text="👤 Profil", callback_data="profile")
        ],
        [
            InlineKeyboardButton(text="📊 Mening testlarim", callback_data="my_tests")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_admin_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users"),
            InlineKeyboardButton(text="🔄 Test limitini o'zgartirish", callback_data="admin_set_limit")
        ],
        [
            InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="💎 Premium statusini o'zgartirish", callback_data="admin_set_premium")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_skip_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ O'tkazib yuborish", callback_data="skip_description")]
    ])

def create_back_keyboard(callback_data="back_to_main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=callback_data)]
    ])

def create_premium_keyboard():
    buttons = [
        [InlineKeyboardButton(text="💬 Admin bilan bog'lanish", url="https://t.me/y0rdam42   ")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_broadcast_confirmation_keyboard(message: any) -> InlineKeyboardMarkup:

    message_str = str(message)
    message_hash = hashlib.md5(message_str.encode()).hexdigest()[:8]
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Ha, yuborish",
                    callback_data=f"confirm_broadcast:{message_hash}"
                ),
                InlineKeyboardButton(
                    text="❌ Yo'q",
                    callback_data="back_to_admin"
                )
            ]
        ]
    )

def create_premium_status_keyboard():
    buttons = [
        [
            InlineKeyboardButton(text="✅ Premium qilish", callback_data="set_premium:1"),
            InlineKeyboardButton(text="❌ Oddiy qilish", callback_data="set_premium:0")
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_pagination_keyboard(current_page, total_pages, base_callback="page"):
    buttons = []

    # Add navigation buttons
    nav_buttons = []

    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"{base_callback}:{current_page-1}"))

    nav_buttons.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))

    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"{base_callback}:{current_page+1}"))

    buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
