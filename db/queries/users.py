"""User-related DB queries."""
import logging
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


async def upsert_user(
    pool: asyncpg.Pool,
    user_id: int,
    username: Optional[str],
    first_name: Optional[str],
) -> None:
    """Insert or update user record."""
    await pool.execute(
        """
        INSERT INTO users (id, username, first_name)
        VALUES ($1, $2, $3)
        ON CONFLICT (id) DO UPDATE
            SET username   = EXCLUDED.username,
                first_name = EXCLUDED.first_name
        """,
        user_id,
        username,
        first_name,
    )


async def get_user(pool: asyncpg.Pool, user_id: int) -> Optional[asyncpg.Record]:
    """Return user row or None."""
    return await pool.fetchrow("SELECT * FROM users WHERE id = $1", user_id)


async def get_all_users(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """Return all users (used by scheduler)."""
    return await pool.fetch("SELECT * FROM users")
