import os
import logging
import time
from typing import List, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

# Загрузка .env
load_dotenv(dotenv_path=os.path.expanduser("~/ai_seller/project/.env"))

# Логгер
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Инициализация OpenAI клиента
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("❌ Переменная окружения OPENAI_API_KEY не найдена.")
    raise EnvironmentError("OPENAI_API_KEY is not set")

client = OpenAI(api_key=api_key)


def generate_response(
    prompt: str,
    system_prompt: Optional[str] = None,
    message_history: Optional[List[Dict[str, str]]] = None,
    model: str = "gpt-4o") -> str:
    """
    Генерирует ответ от OpenAI с контекстом диалога.

    :param prompt: текущее сообщение пользователя
    :param system_prompt: системная инструкция
    :param message_history: список предыдущих сообщений [{"role": ..., "content": ...}]
    :param model: модель OpenAI (по умолчанию gpt-4o)
    :return: ответ ассистента
    """

    # Подготовка сообщений
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if message_history:
        messages.extend(message_history[-8:])  # ограничиваем контекст
    messages.append({"role": "user", "content": prompt})

    logger.info(f"📤 Отправка запроса в OpenAI (model={model}) — сообщений: {len(messages)}")

    # Запрос
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
            )
            reply = response.choices[0].message.content.strip()
            return reply
        except Exception as e:
            logger.warning(f"⚠️ Попытка {attempt}/{max_retries} — ошибка OpenAI: {e}")
            time.sleep(2 ** attempt)
    return "Извините, я не смог ответить сейчас. Попробуйте позже."

