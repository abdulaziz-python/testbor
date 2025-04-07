from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from typing import List, Dict
import hashlib

def create_subscription_keyboard(channels) -> InlineKeyboardMarkup:
    keyboard = []
    
    for channel in channels:
        keyboard.append([
            InlineKeyboardButton(text=f"📣 {channel['title']}", url=f"https://t.me/{channel['id'].lstrip('@')}")
        ])
        
    keyboard.append([
        InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Test yaratish", callback_data="generate_test"),
            InlineKeyboardButton(text="💎 Premium", callback_data="premium")
        ],
        [
            InlineKeyboardButton(text="👤 Profil", callback_data="profile"),
            InlineKeyboardButton(text="📊 Testlarim", callback_data="my_tests")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", callback_data="contact_admin"),
            InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")
        ]
    ])

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
        ],
        [
            InlineKeyboardButton(text="💫 Premium kod yaratish", callback_data="admin_create_promo")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_skip_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ O'tkazib yuborish", callback_data="skip_description")]
    ])

def create_back_keyboard(back_to="back_to_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=back_to)]
    ])

def create_premium_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐️ Yulduzlar bilan sotib olish", callback_data="buy_premium_stars")
        ],
        [
            InlineKeyboardButton(text="💳 Telegram to'lov orqali", callback_data="buy_premium_payment")
        ],
        [
            InlineKeyboardButton(text="💰 Crypto orqali", callback_data="buy_premium_crypto")
        ],
        [
            InlineKeyboardButton(text="🎟️ Promokod ishlatish", callback_data="use_promo_code")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", callback_data="contact_admin")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")
        ]
    ])

def create_payment_options_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💫 Premium (20,000 so'm)", callback_data="pay_premium_20000")
        ],
        [
            InlineKeyboardButton(text="🔥 Premium + 10 yulduz (25,000 so'm)", callback_data="pay_premium_25000")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", callback_data="contact_admin")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium")
        ]
    ])

def create_crypto_payment_options_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💵 USDT (3$)", callback_data="crypto_premium_usdt_5")
        ],
        [
            InlineKeyboardButton(text="💎 TON (0.6 TON)", callback_data="crypto_premium_ton_2")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", callback_data="contact_admin")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium")
        ]
    ])

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

def create_pagination_keyboard(current_page, total_pages) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    
    if current_page > 1:
        row.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{current_page - 1}"))
        
    row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="page_info"))
    
    if current_page < total_pages:
        row.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{current_page + 1}"))
        
    keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Telegram to'lov uchun narxlar
def get_premium_prices() -> list:
    return [LabeledPrice(label="Premium obuna", amount=2000000)]

def get_premium_plus_prices() -> list:
    return [LabeledPrice(label="Premium obuna + 10 yulduz", amount=2500000)]

def create_contact_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", url="https://t.me/yordam_42")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
    ])

def create_edit_test_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Testni tahrirlash", callback_data="edit_test")
        ],
        [
            InlineKeyboardButton(text="🔄 Qayta yaratish", callback_data="regenerate_test")
        ],
        [
            InlineKeyboardButton(text="📊 Boshqa format", callback_data="change_format")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")
        ]
    ])

def create_admin_panel_keyboard():
    """Admin paneli uchun asosiy tugmalar"""
    buttons = [
        [
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🚫 Limitni o'zgartirish", callback_data="admin_set_limit")
        ],
        [
            InlineKeyboardButton(text="💎 Premium statusini o'zgartirish", callback_data="admin_set_premium"),
            InlineKeyboardButton(text="👑 Admin statusini o'zgartirish", callback_data="admin_set_admin")
        ],
        [
            InlineKeyboardButton(text="🎟️ Promokod yaratish", callback_data="admin_create_promo"),
            InlineKeyboardButton(text="💸 Crypto webhook", callback_data="admin_crypto_webhook")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_admin_status_keyboard():
    """Admin statusini o'zgartirish uchun tugmalar"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Admin qilish", callback_data="set_admin:1"),
            InlineKeyboardButton(text="❌ Oddiy foydalanuvchi qilish", callback_data="set_admin:0")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)
