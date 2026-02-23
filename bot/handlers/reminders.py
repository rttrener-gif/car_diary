"""Reminder management handler."""
import logging

from telegram import Update
from telegram.ext import ContextTypes

from db.connection import get_pool
from db.queries.cars import get_user_cars, get_car
from db.queries.records import get_reminders, deactivate_reminder
from services.reminder_calc import get_service_name
from bot import messages as msg
from bot.keyboards import (
    cars_keyboard,
    main_menu_keyboard,
    reminder_actions_keyboard,
)

logger = logging.getLogger(__name__)


async def show_reminders_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by '🔔 Напоминания' menu button."""
    user = update.effective_user
    pool = await get_pool()
    cars = await get_user_cars(pool, user.id)

    if not cars:
        await update.message.reply_html(msg.NO_CARS_YET, reply_markup=main_menu_keyboard())
        return

    if len(cars) == 1:
        await _send_reminders(update, context, cars[0]["id"], via_callback=False)
    else:
        await update.message.reply_html(
            msg.SELECT_CAR,
            reply_markup=cars_keyboard([dict(c) for c in cars]),
        )


async def show_reminders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by inline button callback 'reminders:{car_id}'."""
    query = update.callback_query
    await query.answer()
    car_id = int(query.data.split(":")[1])
    await _send_reminders(update, context, car_id, via_callback=True)


async def _send_reminders(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    car_id: int,
    via_callback: bool,
) -> None:
    try:
        pool = await get_pool()
        car = await get_car(pool, car_id)
        if not car:
            text = msg.CAR_NOT_FOUND
            if via_callback:
                await update.callback_query.edit_message_text(text)
            else:
                await update.message.reply_html(text)
            return

        reminders = await get_reminders(pool, car_id)

        lines = [msg.REMINDERS_HEADER.format(car_name=car["name"])]
        if not reminders:
            lines.append(msg.REMINDERS_EMPTY)
        else:
            for rem in reminders:
                date_str = rem["next_date"].strftime("%d.%m.%Y") if rem["next_date"] else "—"
                mileage_str = f"{rem['next_mileage']:,} км" if rem["next_mileage"] else "—"
                lines.append(msg.REMINDER_ITEM.format(
                    service=get_service_name(rem["service_type"]),
                    date=date_str,
                    mileage=mileage_str,
                ))

        text = "\n".join(lines)

        if via_callback:
            await update.callback_query.edit_message_text(text, parse_mode="HTML")
        else:
            await update.message.reply_html(text)

    except Exception as exc:
        logger.error("Error showing reminders: %s", exc)
        if via_callback:
            await update.callback_query.edit_message_text(msg.ERROR_GENERIC)
        else:
            await update.message.reply_text(msg.ERROR_GENERIC)


async def deactivate_reminder_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle 'rem_off:{reminder_id}' callback."""
    query = update.callback_query
    await query.answer()
    reminder_id = int(query.data.split(":")[1])

    try:
        pool = await get_pool()
        await deactivate_reminder(pool, reminder_id)
        await query.edit_message_text(msg.REMINDER_DEACTIVATED)
    except Exception as exc:
        logger.error("Error deactivating reminder: %s", exc)
        await query.edit_message_text(msg.ERROR_GENERIC)
