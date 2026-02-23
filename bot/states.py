"""ConversationHandler states."""

# ─── Add Car ─────────────────────────────────────────────────────────────────
(
    CAR_MAKE,
    CAR_MODEL,
    CAR_YEAR,
    CAR_MILEAGE,
    CAR_VIN,
    CAR_NAME,
) = range(6)

# ─── Add Service Record ──────────────────────────────────────────────────────
(
    REC_SELECT_CAR,
    REC_SERVICE_TYPE,
    REC_DATE,
    REC_MILEAGE,
    REC_COST,
    REC_NOTES,
) = range(10, 16)

# ─── View History ────────────────────────────────────────────────────────────
(
    HIST_SELECT_CAR,
    HIST_FILTER,
) = range(20, 22)

# ─── Reminders ───────────────────────────────────────────────────────────────
(
    REM_SELECT_CAR,
    REM_ACTION,
) = range(30, 32)

# ─── Delete Car ──────────────────────────────────────────────────────────────
(
    DEL_SELECT_CAR,
    DEL_CONFIRM,
) = range(40, 42)
