"""Service records and reminders DB queries."""
import logging
from datetime import date
from typing import Optional

import asyncpg

logger = logging.getLogger(__name__)


# ─── Service Records ────────────────────────────────────────────────────────

async def add_record(
    pool: asyncpg.Pool,
    car_id: int,
    service_type: str,
    service_date: date,
    mileage: Optional[int],
    cost: Optional[float],
    notes: Optional[str],
) -> int:
    """Insert a service record and return its id."""
    row = await pool.fetchrow(
        """
        INSERT INTO service_records
            (car_id, service_type, service_date, mileage, cost, notes)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        car_id,
        service_type,
        service_date,
        mileage,
        cost,
        notes,
    )
    return row["id"]


async def get_records(
    pool: asyncpg.Pool,
    car_id: int,
    service_type: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[asyncpg.Record]:
    """Return service records for a car with optional filters."""
    params: list = [car_id]
    query = "SELECT * FROM service_records WHERE car_id = $1"

    if service_type:
        params.append(service_type)
        query += f" AND service_type = ${len(params)}"

    query += " ORDER BY service_date DESC"

    if limit:
        params.append(limit)
        query += f" LIMIT ${len(params)}"

    return await pool.fetch(query, *params)


async def get_records_by_year(
    pool: asyncpg.Pool, car_id: int, year: int
) -> list[asyncpg.Record]:
    """Return records for a given year."""
    return await pool.fetch(
        """
        SELECT * FROM service_records
        WHERE car_id = $1
          AND EXTRACT(YEAR FROM service_date) = $2
        ORDER BY service_date DESC
        """,
        car_id,
        year,
    )


async def get_total_cost(
    pool: asyncpg.Pool,
    car_id: int,
    year: Optional[int] = None,
) -> float:
    """Return total cost of service records, optionally filtered by year."""
    if year:
        row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(cost), 0) AS total
            FROM service_records
            WHERE car_id = $1
              AND EXTRACT(YEAR FROM service_date) = $2
              AND cost IS NOT NULL
            """,
            car_id,
            year,
        )
    else:
        row = await pool.fetchrow(
            """
            SELECT COALESCE(SUM(cost), 0) AS total
            FROM service_records
            WHERE car_id = $1 AND cost IS NOT NULL
            """,
            car_id,
        )
    return float(row["total"])


# ─── Reminders ──────────────────────────────────────────────────────────────

async def upsert_reminder(
    pool: asyncpg.Pool,
    car_id: int,
    service_type: str,
    next_date: Optional[date],
    next_mileage: Optional[int],
) -> None:
    """Create or update reminder for a given service type."""
    await pool.execute(
        """
        INSERT INTO reminders (car_id, service_type, next_date, next_mileage)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (car_id, service_type) DO UPDATE
            SET next_date    = EXCLUDED.next_date,
                next_mileage = EXCLUDED.next_mileage,
                is_active    = true
        """,
        car_id,
        service_type,
        next_date,
        next_mileage,
    )


async def get_reminders(pool: asyncpg.Pool, car_id: int) -> list[asyncpg.Record]:
    """Return active reminders for a car."""
    return await pool.fetch(
        "SELECT * FROM reminders WHERE car_id = $1 AND is_active = true",
        car_id,
    )


async def get_due_reminders(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """
    Return reminders that are due within 14 days or within 1000 km.
    Also joins car and user data for sending notifications.
    """
    return await pool.fetch(
        """
        SELECT r.*, c.user_id, c.name AS car_name,
               c.current_mileage, c.make, c.model
        FROM reminders r
        JOIN cars c ON c.id = r.car_id
        WHERE r.is_active = true
          AND (
              r.next_date <= CURRENT_DATE + INTERVAL '14 days'
              OR (r.next_mileage IS NOT NULL
                  AND c.current_mileage IS NOT NULL
                  AND c.current_mileage >= r.next_mileage - 1000)
          )
          AND (
              r.last_notified_at IS NULL
              OR r.last_notified_at < now() - INTERVAL '7 days'
          )
        """
    )


async def mark_reminder_notified(pool: asyncpg.Pool, reminder_id: int) -> None:
    """Update last_notified_at to now."""
    await pool.execute(
        "UPDATE reminders SET last_notified_at = now() WHERE id = $1",
        reminder_id,
    )


async def deactivate_reminder(pool: asyncpg.Pool, reminder_id: int) -> None:
    """Deactivate a reminder."""
    await pool.execute(
        "UPDATE reminders SET is_active = false WHERE id = $1", reminder_id
    )


# ─── Conversation History ────────────────────────────────────────────────────

async def add_message(
    pool: asyncpg.Pool, user_id: int, role: str, content: str
) -> None:
    """Append a message to conversation history."""
    await pool.execute(
        """
        INSERT INTO conversation_history (user_id, role, content)
        VALUES ($1, $2, $3)
        """,
        user_id,
        role,
        content,
    )


async def get_history(
    pool: asyncpg.Pool, user_id: int, limit: int = 10
) -> list[asyncpg.Record]:
    """Return last N messages in chronological order."""
    rows = await pool.fetch(
        """
        SELECT * FROM (
            SELECT * FROM conversation_history
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        ) sub
        ORDER BY created_at ASC
        """,
        user_id,
        limit,
    )
    return rows


async def trim_history(
    pool: asyncpg.Pool, user_id: int, max_messages: int
) -> None:
    """Keep only the last max_messages entries for a user."""
    await pool.execute(
        """
        DELETE FROM conversation_history
        WHERE id NOT IN (
            SELECT id FROM conversation_history
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        )
        AND user_id = $1
        """,
        user_id,
        max_messages,
    )
