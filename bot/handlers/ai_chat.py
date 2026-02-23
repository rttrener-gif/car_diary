"""AI chat handler — forwards messages to Gemini with car context."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from db.connection import get_pool
from db.queries.cars import get_user_cars
from db.queries.records import (
    get_records,
    get_reminders,
    add_message,
    get_history,
    trim_history,
)
from services.gemini import chat_with_context, build_car_context
from config import settings
from bot import messages as msg

logger = logging.getLogger(__name__)


async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle any text message not caught by other handlers."""
    user = update.effective_user
    user_message = update.message.text or ""

    if not user_message.strip():
        return

    # Send "thinking" placeholder
    thinking_msg = await update.message.reply_text(msg.AI_THINKING)

    try:
        pool = await get_pool()

        # Gather context
        cars = await get_user_cars(pool, user.id)
        car_dicts = [dict(c) for c in cars]

        last_records = []
        active_reminders = []
        for car in car_dicts:
            recs = await get_records(pool, car["id"], limit=5)
            last_records.extend([dict(r) for r in recs])
            rems = await get_reminders(pool, car["id"])
            active_reminders.extend([dict(r) for r in rems])

        context_str = build_car_context(car_dicts, last_records[:5], active_reminders)

        # Conversation history
        history_rows = await get_history(pool, user.id, limit=10)
        history = [{"role": r["role"], "content": r["content"]} for r in history_rows]

        # Call Gemini
        response = await chat_with_context(user_message, context_str, history)

        # Persist exchange
        await add_message(pool, user.id, "user", user_message)
        await add_message(pool, user.id, "model", response)

        # Trim history
        await trim_history(pool, user.id, settings.MAX_CONVERSATION_HISTORY)

        # Edit thinking message with response
        await thinking_msg.edit_text(response)

    except Exception as exc:
        logger.error("AI chat error: %s", exc)
        await thinking_msg.edit_text(msg.AI_ERROR)
