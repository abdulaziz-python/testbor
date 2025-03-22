import asyncpg
import os
from datetime import datetime
from bot.utils.logger import get_logger

logger = get_logger(__name__)

DATABASE_URL = "postgresql://testbor_user:idY7t0ETvH08lXBNIHvgvR45Z7xPb2vd@dpg-cvf6vs0fnakc739khm30-a.oregon-postgres.render.com/testbor"

async def setup_db():
    try:
        # Create connection pool
        pool = await asyncpg.create_pool(DATABASE_URL)
        
        async with pool.acquire() as connection:
            # Create users table
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    joined_date TIMESTAMP,
                    is_premium BOOLEAN DEFAULT FALSE,
                    test_limit INTEGER DEFAULT 30,
                    tests_generated INTEGER DEFAULT 0,
                    last_activity TIMESTAMP
                )
            ''')

            # Create tests table
            await connection.execute('''
                CREATE TABLE IF NOT EXISTS tests (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(user_id),
                    subject TEXT,
                    description TEXT,
                    questions_count INTEGER,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        logger.info("Database setup completed")
        return pool
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        raise

# Initialize pool at module level
pool = None

async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL)
    return pool

async def get_user(user_id: int):
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            return await connection.fetchrow(
                "SELECT * FROM users WHERE user_id = $1",
                user_id
            )
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        return None

async def register_user(user_id: int, username: str, full_name: str):
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            current_time = datetime.now()
            
            await connection.execute('''
                INSERT INTO users (user_id, username, full_name, joined_date, last_activity)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    username = $2,
                    full_name = $3,
                    last_activity = $5
            ''', user_id, username, full_name, current_time, current_time)
            
            logger.info(f"User registered/updated: {user_id} ({username})")
    except Exception as e:
        logger.error(f"Error registering user {user_id}: {e}")

async def update_test_count(user_id: int):
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            await connection.execute('''
                UPDATE users 
                SET tests_generated = tests_generated + 1,
                    last_activity = $2
                WHERE user_id = $1
            ''', user_id, datetime.now())
            logger.info(f"Test count updated for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating test count for user {user_id}: {e}")

async def save_test_info(user_id: int, subject: str, description: str, questions_count: int):
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            await connection.execute('''
                INSERT INTO tests (user_id, subject, description, questions_count)
                VALUES ($1, $2, $3, $4)
            ''', user_id, subject, description, questions_count)
            logger.info(f"Test info saved for user {user_id}: {subject} ({questions_count} questions)")
    except Exception as e:
        logger.error(f"Error saving test info for user {user_id}: {e}")

async def get_all_users():
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            return await connection.fetch("SELECT user_id FROM users")
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []

async def get_user_stats():
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            total_users = await connection.fetchval("SELECT COUNT(*) FROM users")
            premium_users = await connection.fetchval("SELECT COUNT(*) FROM users WHERE is_premium = true")
            total_tests = await connection.fetchval("SELECT COALESCE(SUM(tests_generated), 0) FROM users")
            
            today = datetime.now().date()
            tests_today = await connection.fetchval(
                "SELECT COUNT(*) FROM tests WHERE DATE(created_date) = $1",
                today
            )
            active_users_today = await connection.fetchval(
                "SELECT COUNT(DISTINCT user_id) FROM users WHERE DATE(last_activity) = $1",
                today
            )

            return {
                "total_users": total_users,
                "premium_users": premium_users,
                "free_users": total_users - premium_users,
                "total_tests": total_tests,
                "tests_today": tests_today,
                "active_users_today": active_users_today
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

async def update_user_limit(user_id: int, new_limit: int):
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            await connection.execute(
                "UPDATE users SET test_limit = $1 WHERE user_id = $2",
                new_limit, user_id
            )
            logger.info(f"Test limit updated for user {user_id}: {new_limit}")
    except Exception as e:
        logger.error(f"Error updating test limit for user {user_id}: {e}")

async def get_top_users(limit: int = 10):
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            return await connection.fetch('''
                SELECT user_id, username, full_name, is_premium, tests_generated 
                FROM users 
                ORDER BY tests_generated DESC 
                LIMIT $1
            ''', limit)
    except Exception as e:
        logger.error(f"Error getting top users: {e}")
        return []

async def set_premium_status(user_id: int, is_premium: bool):
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            await connection.execute('''
                UPDATE users 
                SET is_premium = $1,
                    test_limit = CASE WHEN $1 = true THEN NULL ELSE 30 END
                WHERE user_id = $2
            ''', is_premium, user_id)
            logger.info(f"Premium status updated for user {user_id}: {is_premium}")
            return True
    except Exception as e:
        logger.error(f"Error updating premium status for user {user_id}: {e}")
        return False

async def get_user_tests(user_id: int, limit: int = 5):
    try:
        pool = await get_pool()
        async with pool.acquire() as connection:
            return await connection.fetch('''
                SELECT subject, questions_count, created_date 
                FROM tests 
                WHERE user_id = $1 
                ORDER BY created_date DESC 
                LIMIT $2
            ''', user_id, limit)
    except Exception as e:
        logger.error(f"Error getting tests for user {user_id}: {e}")
        return []

