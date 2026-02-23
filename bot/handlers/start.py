"""Start handler — onboarding new and returning users."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from db.connection import get_pool
from db.queries.users import upsert_user, get_user
from db.queries.cars import get_user_cars
from bot import messages as msg
from bot.keyboards import main_menu_keyboard, cars_keyboard

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    if not user:
        return

    try:
        pool = await get_pool()
        await upsert_user(pool, user.id, user.username, user.first_name)
        existing = await get_user(pool, user.id)
        cars = await get_user_cars(pool, user.id)

        name = user.first_name or "друг"

        if not cars:
            # New user or no cars yet
            await update.message.reply_html(
                msg.WELCOME_NEW.format(name=name),
                reply_markup=main_menu_keyboard(),
            )
        else:
            # Returning user — show car list
            text = msg.WELCOME_BACK.format(name=name) + "\n"
            await update.message.reply_html(
                text,
                reply_markup=cars_keyboard([dict(c) for c in cars]),
            )
    except Exception as exc:
        logger.error("Error in start_handler: %s", exc)
        await update.message.reply_text(msg.ERROR_GENERIC)
