import asyncpg
import uuid
import datetime
from bot.utils.logger import get_logger
import json
from config.config import load_config

logger = get_logger(__name__)
DATABASE_URL = "postgresql://testbor_user:idY7t0ETvH08lXBNIHvgvR45Z7xPb2vd@dpg-cvf6vs0fnakc739khm30-a.oregon-postgres.render.com/testbor"

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        try:
            await conn.execute("DROP TABLE IF EXISTS promo_codes CASCADE")
            await conn.execute("DROP TABLE IF EXISTS payments CASCADE") 
            await conn.execute("DROP TABLE IF EXISTS tests CASCADE")
            await conn.execute("DROP TABLE IF EXISTS stars CASCADE")
            await conn.execute("DROP TABLE IF EXISTS users CASCADE")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                registration_date TIMESTAMP,
                is_premium BOOLEAN DEFAULT FALSE,
                test_limit INTEGER DEFAULT 30,
                test_count INTEGER DEFAULT 0,
                is_admin BOOLEAN DEFAULT FALSE
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS stars (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE,
                stars INTEGER DEFAULT 0,
                CONSTRAINT fk_stars_user FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                subject TEXT,
                description TEXT,
                questions_count INTEGER,
                created_at TIMESTAMP,
                CONSTRAINT fk_tests_user FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                amount DECIMAL,
                payment_method TEXT,
                currency TEXT,
                status TEXT,
                payment_id TEXT,
                created_at TIMESTAMP,
                CONSTRAINT fk_payments_user FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS promo_codes (
                id SERIAL PRIMARY KEY,
                code TEXT UNIQUE,
                expiry_date TIMESTAMP,
                status TEXT DEFAULT 'active',
                created_by BIGINT,
                created_at TIMESTAMP,
                used_by BIGINT,
                used_at TIMESTAMP,
                CONSTRAINT fk_promo_created_by FOREIGN KEY (created_by) REFERENCES users(id),
                CONSTRAINT fk_promo_used_by FOREIGN KEY (used_by) REFERENCES users(id)
            )
        ''')
        
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    finally:
        await conn.close()

async def get_connection():
    return await asyncpg.connect(DATABASE_URL)

async def register_user(user_id, username, full_name):
    conn = await get_connection()
    try:
        current_date = datetime.datetime.now()
        
        await conn.execute(
            "INSERT INTO users (id, username, full_name, registration_date) VALUES ($1, $2, $3, $4) ON CONFLICT (id) DO NOTHING",
            user_id, username, full_name, current_date
        )
        
        try:
            existing = await conn.fetchval("SELECT COUNT(*) FROM stars WHERE user_id = $1", user_id)
            if existing == 0:
                await conn.execute("INSERT INTO stars (user_id, stars) VALUES ($1, $2)", user_id, 0)
        except Exception as e:
            logger.error(f"Error inserting stars: {e}")
    finally:
        await conn.close()

async def get_user(user_id):
    conn = await get_connection()
    try:
        return await conn.fetchrow(
            "SELECT id, username, full_name, registration_date, is_premium, test_limit, test_count FROM users WHERE id = $1",
            user_id
        )
    finally:
        await conn.close()

async def update_test_count(user_id):
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE users SET test_count = test_count + 1 WHERE id = $1",
            user_id
        )
    finally:
        await conn.close()

async def save_test_info(user_id, subject, description, questions_count):
    conn = await get_connection()
    try:
        current_date = datetime.datetime.now()
        
        await conn.execute(
            "INSERT INTO tests (user_id, subject, description, questions_count, created_at) VALUES ($1, $2, $3, $4, $5)",
            user_id, subject, description, questions_count, current_date
        )
    finally:
        await conn.close()

async def get_user_tests(user_id, limit=5):
    conn = await get_connection()
    try:
        return await conn.fetch(
            "SELECT subject, questions_count, created_at FROM tests WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
            user_id, limit
        )
    finally:
        await conn.close()

async def get_user_stars(user_id):
    conn = await get_connection()
    try:
        result = await conn.fetchval(
            "SELECT stars FROM stars WHERE user_id = $1",
            user_id
        )
        return result if result is not None else 0
    finally:
        await conn.close()

async def add_user_stars(user_id, stars_count):
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT INTO stars (user_id, stars) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET stars = stars.stars + $2",
            user_id, stars_count
        )
        return await get_user_stars(user_id)
    finally:
        await conn.close()

async def spend_stars_for_premium(user_id, stars_count):
    conn = await get_connection()
    try:
        async with conn.transaction():
            current_stars = await get_user_stars(user_id)
            
            if current_stars < stars_count:
                return False, f"Yetarli yulduzlar yo'q. Kerak: {stars_count}, Mavjud: {current_stars}"
            
            await conn.execute(
                "UPDATE stars SET stars = stars - $1 WHERE user_id = $2",
                stars_count, user_id
            )
            
            await conn.execute(
                "UPDATE users SET is_premium = TRUE, test_limit = 999999 WHERE id = $1",
                user_id
            )

            current_date = datetime.datetime.now()
            await conn.execute(
                "INSERT INTO payments (user_id, amount, payment_method, currency, status, payment_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
                user_id, stars_count, "stars", "STARS", "completed", f"stars_premium_{user_id}", current_date
            )
            
            return True, "Premium muvaffaqiyatli faollashtirildi"
    except Exception as e:
        logger.error(f"Error in spend_stars_for_premium: {e}")
        return False, f"Xatolik yuz berdi: {e}"
    finally:
        await conn.close()

async def set_premium_status(user_id, is_premium):
    conn = await get_connection()
    try:
        test_limit = 999999 if is_premium else 30
        
        await conn.execute(
            "UPDATE users SET is_premium = $1, test_limit = $2 WHERE id = $3",
            is_premium, test_limit, user_id
        )
        return True
    finally:
        await conn.close()

async def update_user_limit(user_id, new_limit):
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE users SET test_limit = $1 WHERE id = $2",
            new_limit, user_id
        )
        return True
    finally:
        await conn.close()

async def record_payment(user_id, amount, payment_method, currency, status, payment_id):
    conn = await get_connection()
    try:
        current_date = datetime.datetime.now()
        
        await conn.execute(
            "INSERT INTO payments (user_id, amount, payment_method, currency, status, payment_id, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            user_id, amount, payment_method, currency, status, payment_id, current_date
        )
        return True
    finally:
        await conn.close()

async def update_payment_status(payment_id, status):
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE payments SET status = $1 WHERE payment_id = $2",
            status, payment_id
        )
        return True
    finally:
        await conn.close()

async def get_user_payments(user_id, limit=5):
    conn = await get_connection()
    try:
        return await conn.fetch(
            "SELECT amount, payment_method, currency, status, created_at FROM payments WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
            user_id, limit
        )
    finally:
        await conn.close()

async def save_promo_code(code, expiry_date, created_by):
    conn = await get_connection()
    try:
        current_date = datetime.datetime.now()
        
        await conn.execute(
            "INSERT INTO promo_codes (code, expiry_date, created_by, created_at) VALUES ($1, $2, $3, $4)",
            code, expiry_date, created_by, current_date
        )
        return True
    finally:
        await conn.close()

async def check_promo_code(code):
    conn = await get_connection()
    try:
        return await conn.fetchrow(
            "SELECT * FROM promo_codes WHERE code = $1 AND status = 'active' AND expiry_date > CURRENT_TIMESTAMP",
            code
        )
    finally:
        await conn.close()

async def use_promo_code(code, user_id):
    conn = await get_connection()
    try:
        promo = await check_promo_code(code)
        if not promo:
            return False, "Promo kod topilmadi yoki muddati o'tgan"
        
        current_date = datetime.datetime.now()
        await conn.execute(
            "UPDATE promo_codes SET status = 'used', used_by = $1, used_at = $2 WHERE code = $3",
            user_id, current_date, code
        )
        
        await set_premium_status(user_id, True)
        return True, "Premium muvaffaqiyatli faollashtirildi"
    finally:
        await conn.close()

async def get_all_users():
    conn = await get_connection()
    try:
        return await conn.fetch(
            "SELECT id, username, full_name, registration_date, is_premium, test_limit, test_count FROM users ORDER BY registration_date DESC"
        )
    finally:
        await conn.close()

async def get_user_count():
    conn = await get_connection()
    try:
        return await conn.fetchval("SELECT COUNT(*) FROM users")
    finally:
        await conn.close()

async def get_premium_user_count():
    conn = await get_connection()
    try:
        return await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = true")
    finally:
        await conn.close()

async def get_test_count():
    conn = await get_connection()
    try:
        return await conn.fetchval("SELECT COUNT(*) FROM tests")
    finally:
        await conn.close()

async def get_payment_stats():
    conn = await get_connection()
    try:
        total_payments = await conn.fetchval("SELECT COUNT(*) FROM payments")
        total_amount = await conn.fetchval("SELECT SUM(amount) FROM payments WHERE status = 'completed'")
        return total_payments or 0, total_amount or 0
    finally:
        await conn.close()

async def get_user_stats():
    conn = await get_connection()
    try:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        premium_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = true")
        free_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = false")
        total_tests = await conn.fetchval("SELECT COUNT(*) FROM tests")
        tests_today = await conn.fetchval("""
            SELECT COUNT(*) FROM tests 
            WHERE created_at >= CURRENT_DATE
        """)
        active_users_today = await conn.fetchval("""
            SELECT COUNT(DISTINCT user_id) FROM tests 
            WHERE created_at >= CURRENT_DATE
        """)
        
        return {
            "total_users": total_users or 0,
            "premium_users": premium_users or 0,
            "free_users": free_users or 0,
            "total_tests": total_tests or 0,
            "tests_today": tests_today or 0,
            "active_users_today": active_users_today or 0
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {
            "total_users": 0,
            "premium_users": 0,
            "free_users": 0,
            "total_tests": 0,
            "tests_today": 0,
            "active_users_today": 0
        }
    finally:
        await conn.close()

async def get_top_users(limit=10):
    conn = await get_connection()
    try:
        return await conn.fetch(
            """
            SELECT u.id, u.username, u.full_name, COUNT(t.id) as test_count
            FROM users u
            LEFT JOIN tests t ON u.id = t.user_id
            GROUP BY u.id, u.username, u.full_name
            ORDER BY test_count DESC
            LIMIT $1
            """,
            limit
        )
    finally:
        await conn.close()

async def get_user_profile(user_id):
    conn = await get_connection()
    try:
        user = await get_user(user_id)
        if not user:
            return None
            
        stars = await get_user_stars(user_id)
        tests = await get_user_tests(user_id, limit=5)
        payments = await get_user_payments(user_id, limit=5)
        
        return {
            "user": user,
            "stars": stars,
            "tests": tests,
            "payments": payments
        }
    finally:
        await conn.close()

async def set_admin_status(user_id, is_admin):
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE users SET is_admin = $1 WHERE id = $2",
            is_admin, user_id
        )
        return True
    finally:
        await conn.close()

async def check_is_admin(user_id):
    conn = await get_connection()
    try:
        result = await conn.fetchval(
            "SELECT is_admin FROM users WHERE id = $1",
            user_id
        )
        return result if result is not None else False
    finally:
        await conn.close()