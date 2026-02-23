# Дневник автомобиля — Telegram Bot

Бот для ведения истории технического обслуживания автомобилей.

## Возможности

- Ведение нескольких автомобилей
- Запись ремонтов и замены расходников
- Автоматические напоминания о плановом ТО
- Валидация и расшифровка VIN-номеров
- Диалоговый ИИ-помощник (Gemini Flash 1.5) с контекстом ваших машин

## Стек

| Компонент | Версия |
|-----------|--------|
| Python | 3.11+ |
| python-telegram-bot | 21.x |
| PostgreSQL (Neon) | asyncpg |
| Google Gemini | Flash 1.5 |
| APScheduler | 3.x |

## Структура проекта

```
car_diary_bot/
├── bot/
│   ├── handlers/
│   │   ├── start.py        # /start, онбординг
│   │   ├── car.py          # добавление/просмотр/удаление машин
│   │   ├── records.py      # записи ТО + история
│   │   ├── reminders.py    # управление напоминаниями
│   │   └── ai_chat.py      # свободный диалог через Gemini
│   ├── keyboards.py        # inline и reply клавиатуры
│   ├── messages.py         # все тексты сообщений
│   ├── states.py           # константы состояний ConversationHandler
│   └── main.py             # точка входа
├── db/
│   ├── connection.py       # asyncpg пул (max_size=3)
│   ├── migrations/
│   │   └── 001_initial.sql
│   └── queries/
│       ├── users.py
│       ├── cars.py
│       └── records.py      # records + reminders + conversation_history
├── services/
│   ├── gemini.py           # обёртка Gemini API
│   ├── vin_validator.py    # валидация и расшифровка VIN
│   ├── reminder_calc.py    # расчёт интервалов ТО
│   └── scheduler.py        # APScheduler задачи
├── config.py               # настройки (pydantic BaseSettings)
├── requirements.txt
├── .env.example
├── car_diary_bot.service   # systemd unit
├── deploy.sh               # скрипт обновления
└── setup.sh                # скрипт первичной установки
```

## Быстрый старт (локально)

### 1. Клонировать репозиторий

```bash
git clone <repo_url> car_diary_bot
cd car_diary_bot
```

### 2. Создать виртуальное окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Настроить переменные окружения

```bash
cp .env.example .env
# Отредактировать .env и заполнить все значения
```

### 4. Запустить бота

```bash
python3 -m bot.main
```

Миграции применяются автоматически при первом запуске.

---

## Деплой на VPS (Debian 11)

### Первичная установка

```bash
# Загрузить проект на сервер
git clone <repo_url> /root/car_diary_bot
cd /root/car_diary_bot

# Создать и заполнить .env
cp .env.example .env
nano .env

# Запустить скрипт установки
bash setup.sh
```

### Обновление

```bash
cd /root/car_diary_bot
bash deploy.sh
```

### Управление сервисом

```bash
systemctl status car_diary_bot    # статус
systemctl restart car_diary_bot   # перезапуск
journalctl -u car_diary_bot -f    # просмотр логов
```

---

## База данных

Используется **Neon PostgreSQL** (serverless). Строка подключения:

```
postgresql://user:pass@ep-xxx.eu-central-1.aws.neon.tech/dbname?sslmode=require
```

SSL-соединение устанавливается автоматически. Пул соединений: `max_size=3`
(оптимизировано для сервера с 0.5 GB RAM).

---

## Типы работ ТО

| Ключ | Название | Интервал |
|------|---------|---------|
| `oil` | Замена масла | 10 000 км / 8 мес |
| `air_filter` | Воздушный фильтр | 20 000 км / 18 мес |
| `cabin_filter` | Салонный фильтр | 15 000 км / 12 мес |
| `spark_plugs` | Свечи зажигания | 45 000 км / 36 мес |
| `brake_pads_front` | Передние колодки | 30 000 км |
| `brake_pads_rear` | Задние колодки | 60 000 км |
| `brake_fluid` | Тормозная жидкость | 30 мес |
| `coolant` | Охлаждающая жидкость | 42 мес |
| `timing_belt` | Ремень/цепь ГРМ | 75 000 км / 60 мес |
| `battery` | Аккумулятор | 48 мес |
| `tires_seasonal` | Сезонная резина | 6 мес |

---

## Напоминания

Проверка выполняется каждое утро в `REMINDER_CHECK_TIME` (по умолчанию 09:00 МСК).

Уведомление отправляется если:
- До плановой даты ≤ 14 дней, **ИЛИ**
- До планового пробега ≤ 1 000 км

Повторное уведомление — не раньше чем через 7 дней.

---

## Переменные окружения

| Переменная | Описание |
|-----------|---------|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `GEMINI_API_KEY` | Ключ Google AI Studio |
| `DATABASE_URL` | PostgreSQL connection string |
| `REMINDER_CHECK_TIME` | Время проверки напоминаний (HH:MM) |
| `MAX_CONVERSATION_HISTORY` | Макс. сообщений в истории диалога |
