import asyncpg
from contextlib import asynccontextmanager
from app.config import get_settings

pool: asyncpg.Pool | None = None


async def init_pool():
    global pool
    settings = get_settings()
    pool = await asyncpg.create_pool(
        settings.supabase_db_url,
        min_size=2,
        max_size=10,
    )


async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None


def get_pool() -> asyncpg.Pool:
    assert pool is not None, "Database pool not initialized"
    return pool


@asynccontextmanager
async def get_connection():
    async with get_pool().acquire() as conn:
        yield conn
