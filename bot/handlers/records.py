"""Service record management: add and view history."""
import logging
from datetime import date, datetime
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
from db.queries.cars import get_user_cars, get_car, update_mileage
from db.queries.records import (
    add_record,
    get_records,
    get_records_by_year,
    get_total_cost,
    upsert_reminder,
)
from services.reminder_calc import calculate_next, get_service_name, SERVICE_NAMES
from bot import messages as msg
from bot import states as st
from bot.keyboards import (
    cars_keyboard,
    service_type_keyboard,
    date_keyboard,
    skip_or_cancel_keyboard,
    history_filter_keyboard,
    service_type_filter_keyboard,
    main_menu_keyboard,
)

logger = logging.getLogger(__name__)

_CTX = "add_rec"


def _set(ctx: ContextTypes.DEFAULT_TYPE, k: str, v) -> None:
    ctx.user_data[f"{_CTX}_{k}"] = v


def _get(ctx: ContextTypes.DEFAULT_TYPE, k: str, default=None):
    return ctx.user_data.get(f"{_CTX}_{k}", default)


def _clear(ctx: ContextTypes.DEFAULT_TYPE) -> None:
    for key in list(ctx.user_data.keys()):
        if key.startswith(_CTX):
            del ctx.user_data[key]


# ─── Add Record conversation ──────────────────────────────────────────────────

async def add_record_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: choose which car to log for."""
    _clear(context)
    user = update.effective_user
    pool = await get_pool()
    cars = await get_user_cars(pool, user.id)

    if not cars:
        await update.message.reply_html(msg.NO_CARS_YET, reply_markup=main_menu_keyboard())
        return ConversationHandler.END

    if len(cars) == 1:
        _set(context, "car_id", cars[0]["id"])
        return await _ask_service_type(update, context)

    await update.message.reply_html(
        msg.SELECT_CAR,
        reply_markup=cars_keyboard([dict(c) for c in cars]),
    )
    return st.REC_SELECT_CAR


async def record_car_selected_msg(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Car selected via text (shouldn't normally happen — we use inline)."""
    await update.message.reply_html(msg.SELECT_CAR)
    return st.REC_SELECT_CAR


async def _ask_service_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    target = update.callback_query or update.message
    text = msg.SELECT_SERVICE_TYPE

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, reply_markup=service_type_keyboard(), parse_mode="HTML"
        )
    else:
        await update.message.reply_html(text, reply_markup=service_type_keyboard())

    return st.REC_SERVICE_TYPE


async def record_car_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle car selection inline callback."""
    query = update.callback_query
    await query.answer()
    _, car_id_str = query.data.split(":")
    if car_id_str == "add":
        await query.edit_message_text(msg.ACTION_CANCELLED)
        return ConversationHandler.END
    _set(context, "car_id", int(car_id_str))
    return await _ask_service_type(update, context)


async def record_service_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle service type selection."""
    query = update.callback_query
    await query.answer()
    _, stype = query.data.split(":", 1)

    if stype == "cancel":
        await query.edit_message_text(msg.ACTION_CANCELLED)
        _clear(context)
        return ConversationHandler.END

    _set(context, "service_type", stype)
    await query.edit_message_text(
        msg.ASK_SERVICE_DATE, reply_markup=None, parse_mode="HTML"
    )
    await query.message.reply_html(msg.ASK_SERVICE_DATE, reply_markup=date_keyboard())
    return st.REC_DATE


async def record_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel_rec(update, context)

    if text == msg.TODAY:
        service_date = date.today()
    else:
        try:
            service_date = datetime.strptime(text, "%d.%m.%Y").date()
        except ValueError:
            await update.message.reply_html(msg.DATE_INVALID, reply_markup=date_keyboard())
            return st.REC_DATE

    _set(context, "date", service_date)
    await update.message.reply_html(msg.ASK_SERVICE_MILEAGE, reply_markup=skip_or_cancel_keyboard())
    return st.REC_MILEAGE


async def record_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel_rec(update, context)
    if text != msg.SKIP:
        cleaned = text.replace(" ", "").replace(",", "")
        if not cleaned.isdigit():
            await update.message.reply_html(msg.MILEAGE_INVALID, reply_markup=skip_or_cancel_keyboard())
            return st.REC_MILEAGE
        _set(context, "mileage", int(cleaned))

    await update.message.reply_html(msg.ASK_SERVICE_COST, reply_markup=skip_or_cancel_keyboard())
    return st.REC_COST


async def record_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel_rec(update, context)
    if text != msg.SKIP:
        try:
            cost = float(text.replace(",", ".").replace(" ", ""))
            _set(context, "cost", cost)
        except ValueError:
            await update.message.reply_html(msg.COST_INVALID, reply_markup=skip_or_cancel_keyboard())
            return st.REC_COST

    await update.message.reply_html(msg.ASK_SERVICE_NOTES, reply_markup=skip_or_cancel_keyboard())
    return st.REC_NOTES


async def record_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == msg.CANCEL:
        return await _cancel_rec(update, context)
    if text != msg.SKIP:
        _set(context, "notes", text)

    # Save to DB
    car_id: int = _get(context, "car_id")
    service_type: str = _get(context, "service_type")
    service_date: date = _get(context, "date")
    mileage: Optional[int] = _get(context, "mileage")
    cost: Optional[float] = _get(context, "cost")
    notes: Optional[str] = _get(context, "notes")

    try:
        pool = await get_pool()
        await add_record(pool, car_id, service_type, service_date, mileage, cost, notes)

        # Update car mileage if provided and newer
        if mileage:
            car = await get_car(pool, car_id)
            if car and (car["current_mileage"] is None or mileage > car["current_mileage"]):
                await update_mileage(pool, car_id, mileage)

        # Auto-create / update reminder
        if service_type != "other":
            car = await get_car(pool, car_id)
            current_mileage = car["current_mileage"] if car else None
            next_date, next_mileage, _, _ = calculate_next(
                service_type, service_date, mileage, current_mileage
            )
            await upsert_reminder(pool, car_id, service_type, next_date, next_mileage)

        _clear(context)
        service_name = get_service_name(service_type)
        await update.message.reply_html(
            msg.RECORD_ADDED.format(service=service_name),
            reply_markup=main_menu_keyboard(),
        )
    except Exception as exc:
        logger.error("Error saving record: %s", exc)
        await update.message.reply_text(msg.ERROR_GENERIC)
        _clear(context)

    return ConversationHandler.END


async def _cancel_rec(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    _clear(context)
    await update.message.reply_html(msg.ACTION_CANCELLED, reply_markup=main_menu_keyboard())
    return ConversationHandler.END


# ─── History viewing via callbacks ───────────────────────────────────────────

async def show_history_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show history filter menu for a car."""
    query = update.callback_query
    await query.answer()

    # Could be triggered from message handler too
    if query:
        car_id = int(query.data.split(":")[1])
    else:
        return

    pool = await get_pool()
    car = await get_car(pool, car_id)
    if not car:
        await query.edit_message_text(msg.CAR_NOT_FOUND)
        return

    await query.edit_message_text(
        msg.HISTORY_HEADER.format(car_name=car["name"]) + msg.CHOOSE_FILTER,
        reply_markup=history_filter_keyboard(car_id),
        parse_mode="HTML",
    )


async def _format_records(records: list, total_cost: float) -> str:
    if not records:
        return msg.HISTORY_EMPTY

    lines = []
    for r in records:
        mileage_part = f", {r['mileage']:,} км" if r.get("mileage") else ""
        cost_part = f", {r['cost']} ₽" if r.get("cost") else ""
        notes_part = f"\n  📝 {r['notes']}" if r.get("notes") else ""
        line = msg.HISTORY_RECORD.format(
            service=get_service_name(r["service_type"]),
            date=r["service_date"].strftime("%d.%m.%Y"),
            mileage_part=mileage_part,
            cost_part=cost_part,
            notes_part=notes_part,
        )
        lines.append(line)

    text = "\n".join(lines)
    if total_cost > 0:
        text += msg.HISTORY_TOTAL_COST.format(total=total_cost)
    return text


async def show_history_last5(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, _, car_id_str = query.data.split(":")
    car_id = int(car_id_str)

    pool = await get_pool()
    car = await get_car(pool, car_id)
    records = await get_records(pool, car_id, limit=5)
    total = await get_total_cost(pool, car_id)

    header = msg.HISTORY_HEADER.format(car_name=car["name"] if car else "—")
    body = await _format_records([dict(r) for r in records], total)

    await query.edit_message_text(
        header + body,
        reply_markup=history_filter_keyboard(car_id),
        parse_mode="HTML",
    )


async def show_history_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, _, car_id_str = query.data.split(":")
    car_id = int(car_id_str)
    year = date.today().year

    pool = await get_pool()
    car = await get_car(pool, car_id)
    records = await get_records_by_year(pool, car_id, year)
    total = await get_total_cost(pool, car_id, year=year)

    header = msg.HISTORY_HEADER.format(car_name=car["name"] if car else "—")
    body = await _format_records([dict(r) for r in records], total)

    await query.edit_message_text(
        f"{header}За {year} год:\n{body}",
        reply_markup=history_filter_keyboard(car_id),
        parse_mode="HTML",
    )


async def show_history_by_type_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    _, _, car_id_str = query.data.split(":")
    car_id = int(car_id_str)

    await query.edit_message_text(
        msg.SELECT_SERVICE_TYPE,
        reply_markup=service_type_filter_keyboard(car_id),
        parse_mode="HTML",
    )


async def show_history_by_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    # callback_data = "histtype:{car_id}:{service_type}"
    parts = query.data.split(":", 2)
    car_id = int(parts[1])
    service_type = parts[2]

    pool = await get_pool()
    car = await get_car(pool, car_id)
    records = await get_records(pool, car_id, service_type=service_type)
    total = await get_total_cost(pool, car_id)

    header = msg.HISTORY_HEADER.format(car_name=car["name"] if car else "—")
    sname = get_service_name(service_type)
    body = await _format_records([dict(r) for r in records], total)

    await query.edit_message_text(
        f"{header}Тип: {sname}\n{body}",
        reply_markup=history_filter_keyboard(car_id),
        parse_mode="HTML",
    )


async def show_history_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Triggered by 'История ТО' menu button."""
    user = update.effective_user
    pool = await get_pool()
    cars = await get_user_cars(pool, user.id)

    if not cars:
        await update.message.reply_html(msg.NO_CARS_YET)
        return

    if len(cars) == 1:
        car = cars[0]
        await update.message.reply_html(
            msg.HISTORY_HEADER.format(car_name=car["name"]) + msg.CHOOSE_FILTER,
            reply_markup=history_filter_keyboard(car["id"]),
        )
    else:
        await update.message.reply_html(
            msg.SELECT_CAR,
            reply_markup=cars_keyboard([dict(c) for c in cars]),
        )


# ─── Conversation handler ─────────────────────────────────────────────────────

def add_record_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📋 История ТО$"), show_history_from_message),
            CommandHandler("addrecord", add_record_start),
            # Entry via inline button from car detail screen
            CallbackQueryHandler(
                lambda u, c: add_record_start(u, c), pattern=r"^addrecord:\d+$"
            ),
        ],
        states={
            st.REC_SELECT_CAR: [
                CallbackQueryHandler(record_car_selected_callback, pattern=r"^car:\d+$"),
            ],
            st.REC_SERVICE_TYPE: [
                CallbackQueryHandler(record_service_type, pattern=r"^stype:"),
            ],
            st.REC_DATE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, record_date)],
            st.REC_MILEAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, record_mileage)],
            st.REC_COST:    [MessageHandler(filters.TEXT & ~filters.COMMAND, record_cost)],
            st.REC_NOTES:   [MessageHandler(filters.TEXT & ~filters.COMMAND, record_notes)],
        },
        fallbacks=[
            MessageHandler(filters.Regex(f"^{msg.CANCEL}$"), _cancel_rec),
            CommandHandler("cancel", _cancel_rec),
        ],
        allow_reentry=True,
    )
