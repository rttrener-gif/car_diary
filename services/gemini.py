"""Gemini API wrapper for conversational AI."""
import logging
from typing import Optional

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Ты — AI-помощник «Дневник автомобиля». Помогаешь пользователям:
- разбираться в вопросах технического обслуживания автомобилей
- интерпретировать записи из истории обслуживания
- давать советы по эксплуатации и ремонту
- объяснять коды ошибок OBD и признаки неисправностей

Отвечай кратко и по делу. Если не знаешь ответа — честно скажи об этом.
Всегда учитывай предоставленный контекст об автомобилях пользователя."""

genai.configure(api_key=settings.GEMINI_API_KEY)


def _build_model() -> genai.GenerativeModel:
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=_SYSTEM_PROMPT,
    )


async def chat_with_context(
    user_message: str,
    context: str,
    history: list[dict[str, str]],
) -> str:
    """
    Send a message to Gemini with car context and conversation history.

    Args:
        user_message: The new user message.
        context:      Formatted context string about user's cars/records.
        history:      List of {"role": "user"|"model", "parts": "text"} dicts.

    Returns:
        The model's text response.
    """
    try:
        model = _build_model()

        # Prepend context to user message if available
        full_message = user_message
        if context:
            full_message = f"[Контекст пользователя]\n{context}\n\n[Вопрос]\n{user_message}"

        # Build Gemini-style history
        gemini_history = [
            {"role": h["role"], "parts": [h["content"]]}
            for h in history
        ]

        chat = model.start_chat(history=gemini_history)
        response = await chat.send_message_async(full_message)
        return response.text

    except Exception as exc:
        logger.error("Gemini API error: %s", exc)
        return "Извините, не удалось получить ответ от ИИ. Попробуйте позже."


def build_car_context(
    cars: list[dict],
    last_records: list[dict],
    active_reminders: list[dict],
) -> str:
    """Build a context string about user's vehicles for the AI prompt."""
    if not cars:
        return ""

    lines: list[str] = ["Автомобили пользователя:"]
    for car in cars:
        line = f"• {car['name']} ({car['make']} {car['model']}"
        if car.get("year"):
            line += f", {car['year']} г."
        if car.get("current_mileage"):
            line += f", пробег {car['current_mileage']:,} км"
        line += ")"
        lines.append(line)

    if last_records:
        lines.append("\nПоследние записи ТО:")
        for rec in last_records:
            lines.append(
                f"• {rec['service_type']} — {rec['service_date']}"
                + (f", {rec['mileage']:,} км" if rec.get("mileage") else "")
                + (f", {rec['cost']} ₽" if rec.get("cost") else "")
            )

    if active_reminders:
        lines.append("\nАктивные напоминания:")
        for rem in active_reminders:
            parts = []
            if rem.get("next_date"):
                parts.append(f"дата: {rem['next_date']}")
            if rem.get("next_mileage"):
                parts.append(f"пробег: {rem['next_mileage']:,} км")
            lines.append(f"• {rem['service_type']}: {', '.join(parts)}")

    return "\n".join(lines)
