"""asyncpg connection pool management."""
import logging
import ssl
from typing import Optional

import asyncpg

from config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


async def create_pool() -> asyncpg.Pool:
    """Create and return the asyncpg connection pool."""
    global _pool
    if _pool is not None:
        return _pool

    ssl_ctx: Optional[ssl.SSLContext] = None
    if settings.DATABASE_URL.startswith("postgresql") and "neon.tech" in settings.DATABASE_URL:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

    # Also handle ?sslmode=require in the URL
    dsn = settings.DATABASE_URL
    if "sslmode=require" in dsn:
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        dsn = dsn.split("?")[0]

    logger.info("Creating asyncpg pool (max_size=3)…")
    _pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=1,
        max_size=3,
        ssl=ssl_ctx,
        command_timeout=30,
    )
    logger.info("Pool created successfully.")
    return _pool


async def get_pool() -> asyncpg.Pool:
    """Return existing pool or create one."""
    if _pool is None:
        await create_pool()
    return _pool  # type: ignore[return-value]


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Pool closed.")


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Apply SQL migration files in order."""
    import pathlib

    migrations_dir = pathlib.Path(__file__).parent / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    async with pool.acquire() as conn:
        for sql_file in sql_files:
            logger.info("Running migration: %s", sql_file.name)
            sql = sql_file.read_text(encoding="utf-8")
            await conn.execute(sql)
    logger.info("All migrations applied.")
