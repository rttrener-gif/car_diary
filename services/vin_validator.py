"""VIN validation and decoding utilities."""
import logging
import re

logger = logging.getLogger(__name__)

_INVALID_CHARS = set("IOQ")
_VALID_PATTERN = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

# Country decoding by first character
_COUNTRY_MAP: dict[str, str] = {
    "1": "США",
    "4": "США",
    "5": "США",
    "2": "Канада",
    "3": "Мексика",
    "J": "Япония",
    "K": "Корея",
    "L": "Китай",
    "S": "Великобритания",
    "V": "Франция",
    "W": "Германия",
    "X": "Россия/СНГ",
    "Z": "Италия",
}

# Year decoding by 10th character (index 9)
# Cycle repeats every 30 years: A=1980/2010, B=1981/2011, …
_YEAR_CHARS = "ABCDEFGHJKLMNPRSTVWXY123456789"
_BASE_YEAR_1 = 1980
_BASE_YEAR_2 = 2010


def _decode_year(char: str) -> str:
    char = char.upper()
    if char not in _YEAR_CHARS:
        return "неизвестно"
    idx = _YEAR_CHARS.index(char)
    year1 = _BASE_YEAR_1 + idx
    year2 = _BASE_YEAR_2 + idx
    return f"{year1} или {year2}"


def validate_vin(vin: str) -> tuple[bool, str]:
    """
    Validate a VIN string.

    Returns:
        (True, "") if valid.
        (False, error_message) otherwise.
    """
    vin = vin.strip().upper()

    if len(vin) != 17:
        return False, f"VIN должен содержать ровно 17 символов (получено {len(vin)})"

    invalid = [c for c in vin if c in _INVALID_CHARS]
    if invalid:
        return False, f"VIN не должен содержать буквы I, O, Q (найдено: {''.join(invalid)})"

    if not _VALID_PATTERN.match(vin):
        return False, "VIN содержит недопустимые символы. Разрешены латинские буквы (кроме I, O, Q) и цифры."

    return True, ""


def decode_vin(vin: str) -> dict[str, str]:
    """
    Decode basic VIN fields.

    Returns a dict with keys:
        country, manufacturer, year, plant
    """
    vin = vin.strip().upper()
    if len(vin) != 17:
        return {}

    country_char = vin[0]
    country = _COUNTRY_MAP.get(country_char, f"неизвестно (символ: {country_char})")

    # Characters 1-2 (index 0-1) = WMI (World Manufacturer Identifier)
    wmi = vin[:3]

    # Character at index 9 = model year
    year = _decode_year(vin[9])

    # Character at index 10 = plant code
    plant = vin[10]

    return {
        "country": country,
        "manufacturer": wmi,
        "year": year,
        "plant": plant,
    }
