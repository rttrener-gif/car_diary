"""Bot entry point — register handlers and start polling."""
import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from config import settings
from db.connection import create_pool, close_pool, run_migrations
from services.scheduler import create_scheduler

# Handlers
from bot.handlers.start import start_handler
from bot.handlers.car import (
    add_car_conversation,
    show_car_list,
    show_car_detail,
    delete_car_confirm,
    delete_car_execute,
)
from bot.handlers.records import (
    add_record_conversation,
    show_history_menu,
    show_history_last5,
    show_history_year,
    show_history_by_type_menu,
    show_history_by_type,
    add_record_start,
)
from bot.handlers.reminders import (
    show_reminders_from_message,
    show_reminders_callback,
    deactivate_reminder_callback,
)
from bot.handlers.ai_chat import ai_chat_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Called once after application is initialized."""
    pool = await create_pool()
    await run_migrations(pool)
    application.bot_data["pool"] = pool

    scheduler = create_scheduler(pool, application.bot)
    scheduler.start()
    application.bot_data["scheduler"] = scheduler
    logger.info("Bot initialized.")


async def post_shutdown(application: Application) -> None:
    """Called on shutdown."""
    scheduler = application.bot_data.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
    await close_pool()
    logger.info("Bot shut down.")


def main() -> None:
    app = (
        Application.builder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # ── ConversationHandlers (must be registered before generic handlers) ──
    app.add_handler(add_car_conversation())
    app.add_handler(add_record_conversation())

    # ── Commands ──
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("cars", show_car_list))

    # ── Reply keyboard buttons ──
    app.add_handler(
        MessageHandler(filters.Regex("^🚗 Мои автомобили$"), show_car_list)
    )
    app.add_handler(
        MessageHandler(filters.Regex("^🔔 Напоминания$"), show_reminders_from_message)
    )

    # ── Inline callbacks ──

    # Cars
    app.add_handler(CallbackQueryHandler(show_car_list, pattern=r"^car:list$"))
    app.add_handler(CallbackQueryHandler(show_car_detail, pattern=r"^car:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_car_confirm, pattern=r"^delete_car:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_car_execute, pattern=r"^confirm_delete:\d+$"))

    # Records — add via inline button from car detail
    app.add_handler(
        CallbackQueryHandler(add_record_start, pattern=r"^addrecord:\d+$")
    )

    # History
    app.add_handler(CallbackQueryHandler(show_history_menu,        pattern=r"^history:\d+$"))
    app.add_handler(CallbackQueryHandler(show_history_last5,       pattern=r"^hist:last5:\d+$"))
    app.add_handler(CallbackQueryHandler(show_history_year,        pattern=r"^hist:year:\d+$"))
    app.add_handler(CallbackQueryHandler(show_history_by_type_menu,pattern=r"^hist:bytype:\d+$"))
    app.add_handler(CallbackQueryHandler(show_history_by_type,     pattern=r"^histtype:\d+:.+$"))

    # Reminders
    app.add_handler(CallbackQueryHandler(show_reminders_callback,   pattern=r"^reminders:\d+$"))
    app.add_handler(CallbackQueryHandler(deactivate_reminder_callback, pattern=r"^rem_off:\d+$"))

    # ── AI catch-all (lowest priority) ──
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat_handler)
    )

    logger.info("Starting bot…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
