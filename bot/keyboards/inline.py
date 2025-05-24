from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config.config import load_config

config = load_config()

def create_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Test yaratish", callback_data="generate_test")],
        [InlineKeyboardButton(text="💎 Premium", callback_data="premium"),
         InlineKeyboardButton(text="📚 Mening testlarim", callback_data="my_tests")],
        [InlineKeyboardButton(text="👤 Profil", callback_data="profile"),
         InlineKeyboardButton(text="🎟️ Promo kod", callback_data="use_promo_code")],
        [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help"),
         InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", callback_data="contact_admin")]
    ])

def create_subscription_keyboard(channels):
    buttons = [
        [InlineKeyboardButton(text=f"📢 {channel['name']}", url=channel['url'])]
        for channel in channels
    ]
    buttons.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_skip_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ O'tkazib yuborish", callback_data="skip_description")]
    ])

def create_back_keyboard(callback_data="back_to_main"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=callback_data)]
    ])

def create_premium_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💫 Yulduzlar orqali sotib olish", callback_data="buy_premium_stars")],
        [InlineKeyboardButton(text="💳 To'lov orqali sotib olish", callback_data="buy_premium_payment"),
         InlineKeyboardButton(text="💎 Crypto orqali sotib olish", callback_data="buy_premium_crypto")],
        [InlineKeyboardButton(text="⭐️ Telegram Stars orqali", callback_data="buy_premium_stars_payment")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
    ])

def create_payment_options_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💫 Premium: 20,000 so'm", callback_data="pay_premium_20000")],
        [InlineKeyboardButton(text="🔥 Premium + 10 yulduz: 25,000 so'm", callback_data="pay_premium_25000")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium")]
    ])

def create_crypto_payment_options_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💱 USDT: 3$", callback_data="crypto_premium_usdt_5")],
        [InlineKeyboardButton(text="💰 TON: 0.6 TON", callback_data="crypto_premium_ton_2")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="premium")]
    ])

def create_contact_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", url="https://t.me/y0rdam_42")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
    ])

def get_premium_prices():
    return [
        {"label": "Premium obuna", "amount": 20000 * 100}
    ]

def get_premium_plus_prices():
    return [
        {"label": "Premium obuna", "amount": 20000 * 100},
        {"label": "Bonus 10 yulduz", "amount": 5000 * 100}
    ]

def create_pagination_keyboard(current_page, total_pages, prefix):
    buttons = []
    if current_page > 1:
        buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"{prefix}:page:{current_page - 1}"))
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"{prefix}:page:{current_page + 1}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

def create_broadcast_confirmation_keyboard(message_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_broadcast:{message_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="back_to_admin")]
    ])

def create_premium_status_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Faollashtirish", callback_data="set_premium_true"),
         InlineKeyboardButton(text="❌ O'chirish", callback_data="set_premium_false")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")]
    ])

def create_admin_status_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Faollashtirish", callback_data="set_admin_true"),
         InlineKeyboardButton(text="❌ O'chirish", callback_data="set_admin_false")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")]
    ])

def create_admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users"),
         InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📝 Test limitini o'zgartirish", callback_data="admin_set_limit"),
         InlineKeyboardButton(text="💎 Premium status", callback_data="admin_set_premium")],
        [InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="🎟️ Promo kod yaratish", callback_data="admin_generate_promo")],
        [InlineKeyboardButton(text="👑 Admin status", callback_data="admin_set_admin")]
    ])
