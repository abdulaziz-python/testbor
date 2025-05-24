import asyncpg
from bot.utils.logger import get_logger
from config.config import load_config
import datetime
import uuid

logger = get_logger(__name__)
config = load_config()

async def init_db():
    try:
        pool = await asyncpg.create_pool(
            user=config.db_user,
            password=config.db_password,
            database=config.db_name,
            host=config.db_host,
            port=config.db_port
        )
        async with pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_premium BOOLEAN DEFAULT FALSE,
                    test_count INTEGER DEFAULT 0,
                    test_limit INTEGER DEFAULT 30,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_admin BOOLEAN DEFAULT FALSE
                );
                CREATE INDEX IF NOT EXISTS idx_users_id ON users(id);
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    subject TEXT,
                    description TEXT,
                    questions_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_tests_user_id ON tests(user_id);
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS stars (
                    user_id BIGINT PRIMARY KEY REFERENCES users(id),
                    stars INTEGER DEFAULT 0
                );
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    amount FLOAT,
                    payment_type TEXT,
                    currency TEXT,
                    status TEXT,
                    payment_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS promo_codes (
                    code TEXT PRIMARY KEY,
                    duration_days INTEGER,
                    used_by BIGINT REFERENCES users(id),
                    used_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
        return pool
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise

async def register_user(user_id, username, full_name):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''
                INSERT INTO users (id, username, full_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE
                SET username = EXCLUDED.username, full_name = EXCLUDED.full_name
                ''',
                user_id, username, full_name
            )

async def get_user(user_id):
    async with (await init_db()).acquire() as conn:
        return await conn.fetchrow('SELECT * FROM users WHERE id = $1', user_id)

async def update_test_count(user_id):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                'UPDATE users SET test_count = test_count + 1 WHERE id = $1',
                user_id
            )

async def save_test_info(user_id, subject, description, questions_count):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''
                INSERT INTO tests (user_id, subject, description, questions_count)
                VALUES ($1, $2, $3, $4)
                ''',
                user_id, subject, description, questions_count
            )

async def get_user_tests(user_id, limit=None):
    async with (await init_db()).acquire() as conn:
        query = 'SELECT * FROM tests WHERE user_id = $1 ORDER BY created_at DESC'
        if limit:
            query += f' LIMIT {limit}'
        return await conn.fetch(query, user_id)

async def get_user_stars(user_id):
    async with (await init_db()).acquire() as conn:
        result = await conn.fetchrow('SELECT stars FROM stars WHERE user_id = $1', user_id)
        return result['stars'] if result else 0

async def add_user_stars(user_id, stars):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''
                INSERT INTO stars (user_id, stars)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET stars = stars.stars + $2
                ''',
                user_id, stars
            )

async def spend_stars_for_premium(user_id, stars_cost):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            current_stars = await get_user_stars(user_id)
            if current_stars < stars_cost:
                return False, "Yetarli yulduzlar yo'q"
            await conn.execute(
                'UPDATE stars SET stars = stars - $2 WHERE user_id = $1',
                user_id, stars_cost
            )
            await conn.execute(
                'UPDATE users SET is_premium = TRUE, test_limit = NULL WHERE id = $1',
                user_id
            )
            return True, "Muvaffaqiyatli"

async def set_premium_status(user_id, status):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                'UPDATE users SET is_premium = $2, test_limit = NULL WHERE id = $1',
                user_id, status
            )

async def record_payment(user_id, amount, payment_type, currency, status, payment_id):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''
                INSERT INTO payments (user_id, amount, payment_type, currency, status, payment_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                ''',
                user_id, amount, payment_type, currency, status, payment_id
            )

async def update_payment_status(payment_id, status):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                'UPDATE payments SET status = $2 WHERE payment_id = $1',
                payment_id, status
            )

async def get_all_users():
    async with (await init_db()).acquire() as conn:
        return await conn.fetch('SELECT * FROM users')

async def get_user_stats():
    async with (await init_db()).acquire() as conn:
        total_users = await conn.fetchval('SELECT COUNT(*) FROM users')
        premium_users = await conn.fetchval('SELECT COUNT(*) FROM users WHERE is_premium = TRUE')
        total_tests = await conn.fetchval('SELECT COUNT(*) FROM tests')
        total_stars = await conn.fetchval('SELECT SUM(stars) FROM stars') or 0
        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "total_tests": total_tests,
            "total_stars": total_stars
        }

async def get_top_users(limit=10):
    async with (await init_db()).acquire() as conn:
        return await conn.fetch(
            'SELECT * FROM users ORDER BY test_count DESC LIMIT $1',
            limit
        )

async def update_user_limit(user_id, new_limit):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                'UPDATE users SET test_limit = $2 WHERE id = $1',
                user_id, new_limit
            )

async def save_promo_code(code, duration_days):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                '''
                INSERT INTO promo_codes (code, duration_days)
                VALUES ($1, $2)
                ''',
                code, duration_days
            )

async def use_promo_code(code, user_id):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            promo = await conn.fetchrow(
                'SELECT * FROM promo_codes WHERE code = $1 AND used_by IS NULL',
                code
            )
            if not promo:
                return False, "Promo kod topilmadi yoki allaqachon ishlatilgan"
            await conn.execute(
                '''
                UPDATE promo_codes
                SET used_by = $2, used_at = CURRENT_TIMESTAMP
                WHERE code = $1
                ''',
                code, user_id
            )
            await set_premium_status(user_id, True)
            return True, "Muvaffaqiyatli"

async def set_admin_status(user_id, status):
    async with (await init_db()).acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                'UPDATE users SET is_admin = $2 WHERE id = $1',
                user_id, status
            )

async def check_is_admin(user_id):
    async with (await init_db()).acquire() as conn:
        result = await conn.fetchrow('SELECT is_admin FROM users WHERE id = $1', user_id)
        return result['is_admin'] if result else False
