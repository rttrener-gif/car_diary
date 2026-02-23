"""All inline and reply keyboards."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

from services.reminder_calc import SERVICE_NAMES, all_service_types
from bot.messages import SKIP, TODAY, BACK, CANCEL, YES_DELETE


# ─── Main Menu ───────────────────────────────────────────────────────────────

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        ["🚗 Мои автомобили", "➕ Добавить машину"],
        ["📋 История ТО", "🔔 Напоминания"],
        ["💬 Спросить ИИ"],
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


# ─── Car List ────────────────────────────────────────────────────────────────

def cars_keyboard(cars: list[dict]) -> InlineKeyboardMarkup:
    """Inline keyboard listing cars."""
    buttons = [
        [InlineKeyboardButton(car["name"], callback_data=f"car:{car['id']}")]
        for car in cars
    ]
    buttons.append([InlineKeyboardButton("➕ Добавить машину", callback_data="car:add")])
    return InlineKeyboardMarkup(buttons)


def car_actions_keyboard(car_id: int) -> InlineKeyboardMarkup:
    """Actions for a specific car."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 История", callback_data=f"history:{car_id}"),
            InlineKeyboardButton("🔔 Напоминания", callback_data=f"reminders:{car_id}"),
        ],
        [
            InlineKeyboardButton("➕ Запись ТО", callback_data=f"addrecord:{car_id}"),
            InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_car:{car_id}"),
        ],
        [InlineKeyboardButton(BACK, callback_data="car:list")],
    ])


def confirm_delete_keyboard(car_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(YES_DELETE, callback_data=f"confirm_delete:{car_id}"),
            InlineKeyboardButton(CANCEL, callback_data=f"car:{car_id}"),
        ]
    ])


# ─── Add Car ─────────────────────────────────────────────────────────────────

def skip_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[SKIP]], resize_keyboard=True, one_time_keyboard=True)


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([[CANCEL]], resize_keyboard=True)


# ─── Service Record ──────────────────────────────────────────────────────────

def service_type_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard with service type options."""
    service_types = [t for t in all_service_types() if t != "other"]
    buttons = []
    row: list[InlineKeyboardButton] = []
    for stype in service_types:
        row.append(InlineKeyboardButton(
            SERVICE_NAMES.get(stype, stype), callback_data=f"stype:{stype}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Другое", callback_data="stype:other")])
    buttons.append([InlineKeyboardButton(CANCEL, callback_data="stype:cancel")])
    return InlineKeyboardMarkup(buttons)


def date_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[TODAY], [CANCEL]], resize_keyboard=True, one_time_keyboard=True
    )


def skip_or_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[SKIP], [CANCEL]], resize_keyboard=True, one_time_keyboard=True
    )


# ─── History ─────────────────────────────────────────────────────────────────

def history_filter_keyboard(car_id: int) -> InlineKeyboardMarkup:
    import datetime
    current_year = datetime.date.today().year
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Последние 5", callback_data=f"hist:last5:{car_id}")],
        [InlineKeyboardButton(f"За {current_year} год", callback_data=f"hist:year:{car_id}")],
        [InlineKeyboardButton("По типу работ", callback_data=f"hist:bytype:{car_id}")],
        [InlineKeyboardButton(BACK, callback_data=f"car:{car_id}")],
    ])


def service_type_filter_keyboard(car_id: int) -> InlineKeyboardMarkup:
    """Filter history by service type."""
    service_types = all_service_types()
    buttons = [
        [InlineKeyboardButton(SERVICE_NAMES.get(t, t), callback_data=f"histtype:{car_id}:{t}")]
        for t in service_types
    ]
    buttons.append([InlineKeyboardButton(BACK, callback_data=f"history:{car_id}")])
    return InlineKeyboardMarkup(buttons)


# ─── Reminders ───────────────────────────────────────────────────────────────

def reminder_actions_keyboard(car_id: int, reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔕 Отключить", callback_data=f"rem_off:{reminder_id}")],
        [InlineKeyboardButton(BACK, callback_data=f"reminders:{car_id}")],
    ])
