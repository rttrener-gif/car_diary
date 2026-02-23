"""Car-related DB queries."""
import logging
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


async def add_car(
    pool: asyncpg.Pool,
    user_id: int,
    name: str,
    make: str,
    model: str,
    year: Optional[int],
    vin: Optional[str],
    current_mileage: Optional[int],
) -> int:
    """Insert a new car and return its id."""
    row = await pool.fetchrow(
        """
        INSERT INTO cars (user_id, name, make, model, year, vin, current_mileage)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id
        """,
        user_id,
        name,
        make,
        model,
        year,
        vin,
        current_mileage,
    )
    return row["id"]


async def get_user_cars(pool: asyncpg.Pool, user_id: int) -> list[asyncpg.Record]:
    """Return all cars belonging to a user."""
    return await pool.fetch(
        "SELECT * FROM cars WHERE user_id = $1 ORDER BY created_at", user_id
    )


async def get_car(pool: asyncpg.Pool, car_id: int) -> Optional[asyncpg.Record]:
    """Return a single car by id."""
    return await pool.fetchrow("SELECT * FROM cars WHERE id = $1", car_id)


async def update_mileage(pool: asyncpg.Pool, car_id: int, mileage: int) -> None:
    """Update current mileage for a car."""
    await pool.execute(
        "UPDATE cars SET current_mileage = $1 WHERE id = $2", mileage, car_id
    )


async def delete_car(pool: asyncpg.Pool, car_id: int) -> None:
    """Delete a car (cascades to records and reminders)."""
    await pool.execute("DELETE FROM cars WHERE id = $1", car_id)


async def get_all_cars_with_users(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """Return all cars joined with user_id (for scheduler)."""
    return await pool.fetch(
        """
        SELECT c.*, u.id AS uid
        FROM cars c
        JOIN users u ON u.id = c.user_id
        """
    )
