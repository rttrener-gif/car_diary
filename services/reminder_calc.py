"""Reminder interval calculation for service types."""
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Intervals for each service type
INTERVALS: dict[str, dict[str, Optional[int]]] = {
    "oil":              {"km": 10_000, "months": 8},
    "air_filter":       {"km": 20_000, "months": 18},
    "cabin_filter":     {"km": 15_000, "months": 12},
    "spark_plugs":      {"km": 45_000, "months": 36},
    "brake_pads_front": {"km": 30_000, "months": None},
    "brake_pads_rear":  {"km": 60_000, "months": None},
    "brake_fluid":      {"km": None,   "months": 30},
    "coolant":          {"km": None,   "months": 42},
    "timing_belt":      {"km": 75_000, "months": 60},
    "battery":          {"km": None,   "months": 48},
    "tires_seasonal":   {"km": None,   "months": 6},
}

# Human-readable names (Russian)
SERVICE_NAMES: dict[str, str] = {
    "oil":              "Замена масла",
    "air_filter":       "Воздушный фильтр",
    "cabin_filter":     "Салонный фильтр",
    "spark_plugs":      "Свечи зажигания",
    "brake_pads_front": "Передние тормозные колодки",
    "brake_pads_rear":  "Задние тормозные колодки",
    "brake_fluid":      "Тормозная жидкость",
    "coolant":          "Охлаждающая жидкость",
    "timing_belt":      "Ремень/цепь ГРМ",
    "battery":          "Аккумулятор",
    "tires_seasonal":   "Сезонная смена резины",
    "other":            "Другое",
}


def calculate_next(
    service_type: str,
    last_date: date,
    last_mileage: Optional[int],
    current_mileage: Optional[int],
) -> tuple[Optional[date], Optional[int], Optional[int], Optional[int]]:
    """
    Calculate next service date and mileage.

    Returns:
        (next_date, next_mileage, days_left, km_left)
        Any value can be None if not applicable.
    """
    interval = INTERVALS.get(service_type)
    if not interval:
        return None, None, None, None

    today = date.today()

    # Calculate next_date
    next_date: Optional[date] = None
    days_left: Optional[int] = None
    if interval["months"] is not None:
        next_date = last_date + relativedelta(months=interval["months"])
        days_left = (next_date - today).days

    # Calculate next_mileage
    next_mileage: Optional[int] = None
    km_left: Optional[int] = None
    if interval["km"] is not None and last_mileage is not None:
        next_mileage = last_mileage + interval["km"]
        if current_mileage is not None:
            km_left = next_mileage - current_mileage

    return next_date, next_mileage, days_left, km_left


def get_service_name(service_type: str) -> str:
    """Return human-readable service name."""
    return SERVICE_NAMES.get(service_type, service_type)


def all_service_types() -> list[str]:
    """Return list of all known service types."""
    return list(INTERVALS.keys()) + ["other"]
