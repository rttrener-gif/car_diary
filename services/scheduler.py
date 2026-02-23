"""APScheduler tasks for reminder notifications."""
import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

from config import settings
from db.queries.records import get_due_reminders, mark_reminder_notified
from services.reminder_calc import get_service_name

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _format_reminder_message(row: "asyncpg.Record") -> str:
    parts = [
        f"🔔 <b>Напоминание о ТО</b>",
        f"Автомобиль: <b>{row['car_name']}</b> ({row['make']} {row['model']})",
        f"Вид работ: <b>{get_service_name(row['service_type'])}</b>",
    ]
    if row["next_date"]:
        parts.append(f"Плановая дата: {row['next_date'].strftime('%d.%m.%Y')}")
    if row["next_mileage"] and row["current_mileage"]:
        km_left = row["next_mileage"] - row["current_mileage"]
        parts.append(f"Осталось км: {km_left:,}")
    parts.append("\nПора записаться на сервис!")
    return "\n".join(parts)


async def _check_and_send_reminders(pool: "asyncpg.Pool", bot: Bot) -> None:
    """Fetch due reminders and notify users."""
    try:
        due = await get_due_reminders(pool)
        logger.info("Reminder check: %d due reminders found.", len(due))

        for row in due:
            try:
                text = _format_reminder_message(row)
                await bot.send_message(
                    chat_id=row["user_id"],
                    text=text,
                    parse_mode="HTML",
                )
                await mark_reminder_notified(pool, row["id"])
                logger.info(
                    "Reminder sent: user=%s, reminder=%s", row["user_id"], row["id"]
                )
            except Exception as exc:
                logger.warning(
                    "Failed to send reminder %s to user %s: %s",
                    row["id"],
                    row["user_id"],
                    exc,
                )
    except Exception as exc:
        logger.error("Reminder check failed: %s", exc)


def create_scheduler(pool: "asyncpg.Pool", bot: Bot) -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    global _scheduler
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

    time_parts = settings.REMINDER_CHECK_TIME.split(":")
    hour = int(time_parts[0])
    minute = int(time_parts[1]) if len(time_parts) > 1 else 0

    scheduler.add_job(
        _check_and_send_reminders,
        trigger="cron",
        hour=hour,
        minute=minute,
        kwargs={"pool": pool, "bot": bot},
        id="daily_reminders",
        replace_existing=True,
    )

    _scheduler = scheduler
    return scheduler
