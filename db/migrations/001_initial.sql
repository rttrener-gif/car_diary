-- Car Diary Bot — Initial Schema
-- Migration 001

CREATE TABLE IF NOT EXISTS users (
    id         BIGINT PRIMARY KEY,
    username   TEXT,
    first_name TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cars (
    id              SERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    make            TEXT NOT NULL,
    model           TEXT NOT NULL,
    year            INTEGER,
    vin             CHAR(17) UNIQUE,
    current_mileage INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_cars_user_id ON cars(user_id);

CREATE TABLE IF NOT EXISTS service_records (
    id           SERIAL PRIMARY KEY,
    car_id       INTEGER REFERENCES cars(id) ON DELETE CASCADE,
    service_type TEXT NOT NULL,
    service_date DATE NOT NULL,
    mileage      INTEGER,
    cost         NUMERIC(10, 2),
    notes        TEXT,
    created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_records_car_id ON service_records(car_id);
CREATE INDEX IF NOT EXISTS idx_service_records_type   ON service_records(service_type);

CREATE TABLE IF NOT EXISTS reminders (
    id               SERIAL PRIMARY KEY,
    car_id           INTEGER REFERENCES cars(id) ON DELETE CASCADE,
    service_type     TEXT NOT NULL,
    next_date        DATE,
    next_mileage     INTEGER,
    is_active        BOOLEAN DEFAULT true,
    last_notified_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_reminders_car_service
    ON reminders(car_id, service_type);
CREATE INDEX IF NOT EXISTS idx_reminders_car_id ON reminders(car_id);

CREATE TABLE IF NOT EXISTS conversation_history (
    id         SERIAL PRIMARY KEY,
    user_id    BIGINT REFERENCES users(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('user', 'model')),
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_conversation_user_id ON conversation_history(user_id);
