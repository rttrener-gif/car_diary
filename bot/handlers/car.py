"""Car management: add, view, delete."""
import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from db.connection import get_pool
from db.queries.cars import add_car, get_user_cars, get_car, delete_car
from services.vin_validator import validate_vin, decode_vin
from bot import messages as msg
from bot import states as st
from bot.keyboards import (
    skip_keyboard,
    cancel_keyboard,
    cars_keyboard,
    car_actions_keyboard,
    confirm_delete_keyboard,
    main_menu_keyboard,
)

logger = logging.getLogger(__name__)

_CTX_PREFIX = "add_car"


def _set(context: ContextTypes.DEFAULT_TYPE, key: str, value) -> None:
    context.user_data[f"{_CTX_PREFIX}_{key}"] = value


def _get(context: ContextTypes.DEFAULT_TYPE, key: str, default=None):
    return context.user_data.get(f"{_CTX_PREFIX}_{key}", default)


def _clear(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in list(context.user_data.keys()):
        if key.startswith(_CTX_PREFIX):
            del context.user_data[key]


# ─── Add Car conversation ─────────────────────────────────────────────────────

async def add_car_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for add-car conversation."""
    _clear(context)
    text = update.message.text if update.message else ""
    # Could be triggered by button or /addcar command
    await update.message.reply_html(msg.ASK_CAR_MAKE, reply_markup=cancel_keyboard())
    return st.CAR_MAKE


async def car_make(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel(update, context)
    _set(context, "make", text)
    await update.message.reply_html(msg.ASK_CAR_MODEL, reply_markup=cancel_keyboard())
    return st.CAR_MODEL


async def car_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel(update, context)
    _set(context, "model", text)
    await update.message.reply_html(msg.ASK_CAR_YEAR, reply_markup=skip_keyboard())
    return st.CAR_YEAR


async def car_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel(update, context)
    if text != msg.SKIP:
        if not text.isdigit() or not (1886 <= int(text) <= 2100):
            await update.message.reply_html(msg.YEAR_INVALID, reply_markup=skip_keyboard())
            return st.CAR_YEAR
        _set(context, "year", int(text))
    await update.message.reply_html(msg.ASK_CAR_MILEAGE, reply_markup=skip_keyboard())
    return st.CAR_MILEAGE


async def car_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel(update, context)
    if text != msg.SKIP:
        cleaned = text.replace(" ", "").replace(",", "")
        if not cleaned.isdigit():
            await update.message.reply_html(msg.MILEAGE_INVALID, reply_markup=skip_keyboard())
            return st.CAR_MILEAGE
        _set(context, "mileage", int(cleaned))
    await update.message.reply_html(msg.ASK_CAR_VIN, reply_markup=skip_keyboard())
    return st.CAR_VIN


async def car_vin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel(update, context)
    if text != msg.SKIP:
        valid, error = validate_vin(text)
        if not valid:
            await update.message.reply_html(
                msg.VIN_INVALID.format(error=error),
                reply_markup=skip_keyboard(),
            )
            return st.CAR_VIN
        _set(context, "vin", text.upper())
        info = decode_vin(text)
        if info:
            await update.message.reply_html(
                msg.VIN_DECODED.format(**info),
            )
    await update.message.reply_html(msg.ASK_CAR_NAME, reply_markup=cancel_keyboard())
    return st.CAR_NAME


async def car_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel(update, context)

    user = update.effective_user
    try:
        pool = await get_pool()
        car_id = await add_car(
            pool,
            user_id=user.id,
            name=text,
            make=_get(context, "make", ""),
            model=_get(context, "model", ""),
            year=_get(context, "year"),
            vin=_get(context, "vin"),
            current_mileage=_get(context, "mileage"),
        )
        _clear(context)
        context.user_data["last_car_id"] = car_id
        await update.message.reply_html(
            msg.CAR_ADDED.format(name=text),
            reply_markup=main_menu_keyboard(),
        )
    except Exception as exc:
        logger.error("Error saving car: %s", exc)
        await update.message.reply_text(msg.ERROR_GENERIC)
        _clear(context)

    return ConversationHandler.END


async def _cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _clear(context)
    await update.message.reply_html(
        msg.ACTION_CANCELLED, reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


# ─── View / Delete via inline callbacks ──────────────────────────────────────

async def show_car_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of user's cars (from message or callback)."""
    user = update.effective_user
    query = update.callback_query
    if query:
        await query.answer()

    try:
        pool = await get_pool()
        cars = await get_user_cars(pool, user.id)
        car_dicts = [dict(c) for c in cars]

        if not car_dicts:
            text = msg.NO_CARS_YET
        else:
            text = msg.CAR_LIST_HEADER

        if query:
            await query.edit_message_text(text, reply_markup=cars_keyboard(car_dicts), parse_mode="HTML")
        else:
            await update.message.reply_html(text, reply_markup=cars_keyboard(car_dicts))
    except Exception as exc:
        logger.error("Error showing cars: %s", exc)


async def show_car_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show details and actions for a single car."""
    query = update.callback_query
    await query.answer()
    car_id = int(query.data.split(":")[1])

    try:
        pool = await get_pool()
        car = await get_car(pool, car_id)
        if not car:
            await query.edit_message_text(msg.CAR_NOT_FOUND)
            return

        text = msg.CAR_INFO.format(
            name=car["name"],
            make=car["make"],
            model=car["model"],
            year=car["year"] or "—",
            mileage=f"{car['current_mileage']:,}" if car["current_mileage"] else "—",
            vin=car["vin"] or "—",
        )
        await query.edit_message_text(
            text, reply_markup=car_actions_keyboard(car_id), parse_mode="HTML"
        )
    except Exception as exc:
        logger.error("Error in show_car_detail: %s", exc)


async def delete_car_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask confirmation before deleting car."""
    query = update.callback_query
    await query.answer()
    car_id = int(query.data.split(":")[1])

    try:
        pool = await get_pool()
        car = await get_car(pool, car_id)
        if not car:
            await query.edit_message_text(msg.CAR_NOT_FOUND)
            return
        await query.edit_message_text(
            msg.CONFIRM_DELETE.format(name=car["name"]),
            reply_markup=confirm_delete_keyboard(car_id),
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.error("Error in delete_car_confirm: %s", exc)


async def delete_car_execute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute car deletion after confirmation."""
    query = update.callback_query
    await query.answer()
    car_id = int(query.data.split(":")[1])

    try:
        pool = await get_pool()
        car = await get_car(pool, car_id)
        name = car["name"] if car else "—"
        await delete_car(pool, car_id)

        # Refresh car list
        user = update.effective_user
        cars = await get_user_cars(pool, user.id)
        car_dicts = [dict(c) for c in cars]

        text = msg.CAR_DELETED.format(name=name) + "\n\n" + (
            msg.CAR_LIST_HEADER if car_dicts else msg.NO_CARS_YET
        )
        await query.edit_message_text(
            text, reply_markup=cars_keyboard(car_dicts), parse_mode="HTML"
        )
    except Exception as exc:
        logger.error("Error deleting car: %s", exc)


# ─── Conversation handler factory ────────────────────────────────────────────

def add_car_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^➕ Добавить машину$"), add_car_start
            ),
            CommandHandler("addcar", add_car_start),
        ],
        states={
            st.CAR_MAKE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, car_make)],
            st.CAR_MODEL:   [MessageHandler(filters.TEXT & ~filters.COMMAND, car_model)],
            st.CAR_YEAR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, car_year)],
            st.CAR_MILEAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, car_mileage)],
            st.CAR_VIN:     [MessageHandler(filters.TEXT & ~filters.COMMAND, car_vin)],
            st.CAR_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, car_name)],
        },
        fallbacks=[
            MessageHandler(filters.Regex(f"^{msg.CANCEL}$"), _cancel),
            CommandHandler("cancel", _cancel),
        ],
        allow_reentry=True,
    )
