import os
import json
import logging
import asyncio
from collections import defaultdict
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters, PicklePersistence
from llm_logic import generate_response
from claude_emotion import analyze_emotion, humanize_reply

# Загрузка .env
load_dotenv(dotenv_path=os.path.expanduser("~/ai_seller/project/.env"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Логгер
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальное хранилище состояний пользователей (в продакшене лучше использовать Redis)
user_states = defaultdict(dict)


def load_personality() -> dict:
    path = os.path.expanduser("~/ai_seller/project/python-core/config/personality_templates.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["telegram_sales_bot"]


def build_system_prompt(data: dict) -> str:
    parts = [
        data["role"],
        data["company"],
        data["product"],
        "Тон общения: " + data["tone"],
        "Контекст: " + data["behavior_context"],
        "Правила: " + " ".join(data["rules"]),
        "Критически важно: " + " ".join(data["CRITICAL_INSTRUCTIONS"]["ОБЯЗАТЕЛЬНО"])
    ]
    return "\n".join(parts)


PERSONA = load_personality()
KEY_QUESTIONS = PERSONA["key_questions"]
SYSTEM_PROMPT = build_system_prompt(PERSONA)


def get_user_state(user_id: int) -> dict:
    """Получить состояние пользователя"""
    if user_id not in user_states:
        user_states[user_id] = {
            "dialog_started": False,
            "lead_info": {},
            "question_index": 0,
            "messages_count": 0,
            "conversation_history": []
        }
    return user_states[user_id]


def update_user_state(user_id: int, **kwargs) -> None:
    """Обновить состояние пользователя"""
    state = get_user_state(user_id)
    state.update(kwargs)
    user_states[user_id] = state


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text.strip()
    user_id = update.effective_user.id
    logger.info(f"📩 [{user_id}] {user_input}")

    # Получаем состояние пользователя
    state = get_user_state(user_id)
    
    # Добавляем сообщение в историю
    state["conversation_history"].append({"role": "user", "content": user_input})
    state["messages_count"] += 1

    # ПЕРВОЕ СООБЩЕНИЕ - только приветствие
    if not state["dialog_started"]:
        state["dialog_started"] = True
        update_user_state(user_id, **state)

        welcome = (
            "Привет! Меня зовут Лена, я менеджер швейной фабрики SoVAni 😊\n"
            "Расскажите, что вы хотите пошить — подскажу, с чего начать."
        )
        styled_welcome = humanize_reply(welcome, SYSTEM_PROMPT, user_input)
        
        # Добавляем ответ в историю
        state["conversation_history"].append({"role": "assistant", "content": styled_welcome})
        update_user_state(user_id, **state)
        
        await update.message.reply_text(styled_welcome)
        return

    # ОСНОВНАЯ ЛОГИКА ДИАЛОГА
    
    # Формируем контекст для ChatGPT
    conversation_context = ""
    if state["conversation_history"]:
        # Берем последние 4 сообщения для контекста
        recent_history = state["conversation_history"][-4:]
        for msg in recent_history:
            role = "Клиент" if msg["role"] == "user" else "Менеджер"
            conversation_context += f"{role}: {msg['content']}\n"
    
    # Получаем ответ от ChatGPT
    raw_response = generate_response(
        user_input, 
        system_prompt=SYSTEM_PROMPT,
        conversation_history=conversation_context
    )
    
    # Проверяем, нужно ли задать ключевой вопрос
    current_question_index = state["question_index"]
    needs_key_question = should_ask_key_question(user_input, state["lead_info"], current_question_index)
    
    if needs_key_question and current_question_index < len(KEY_QUESTIONS):
        # Добавляем ключевой вопрос к ответу
        key_question = KEY_QUESTIONS[current_question_index]
        
        # Проверяем, не ответил ли уже клиент на этот вопрос в своем сообщении
        if not answer_covers_question(user_input, key_question):
            combined_response = f"{raw_response}\n\n{key_question}"
        else:
            # Клиент уже ответил, сохраняем ответ
            state["lead_info"][key_question] = user_input
            combined_response = raw_response
        
        state["question_index"] += 1
    else:
        combined_response = raw_response
    
    # Стилизуем ответ через Claude
    styled_response = humanize_reply(combined_response, SYSTEM_PROMPT, user_input)
    
    # Обновляем историю
    state["conversation_history"].append({"role": "assistant", "content": styled_response})
    update_user_state(user_id, **state)
    
    # Отправляем ответ
    await update.message.reply_text(styled_response)
    
    # Проверяем, собрали ли все данные
    if len(state["lead_info"]) >= len(KEY_QUESTIONS):
        logger.info(f"✅ Все данные собраны для пользователя {user_id}: {state['lead_info']}")
        await notify_managers(update, state["lead_info"])


def should_ask_key_question(user_message: str, lead_info: dict, question_index: int) -> bool:
    """Определяет, нужно ли задать ключевой вопрос"""
    # Если все вопросы уже заданы
    if question_index >= len(KEY_QUESTIONS):
        return False
    
    # Если клиент только поздоровался - не задаем сразу вопрос
    greetings = ["привет", "здравствуйте", "добрый день", "hi", "hello"]
    if any(greeting in user_message.lower() for greeting in greetings) and len(user_message.split()) <= 2:
        return False
    
    # Если клиент уже дал релевантную информацию - не дублируем вопрос
    current_question = KEY_QUESTIONS[question_index]
    if answer_covers_question(user_message, current_question):
        return False
    
    # В остальных случаях задаем вопрос, но не чаще чем каждые 2 сообщения
    return True


def answer_covers_question(user_message: str, question: str) -> bool:
    """Проверяет, отвечает ли сообщение пользователя на заданный вопрос"""
    user_lower = user_message.lower()
    question_lower = question.lower()
    
    # Ключевые слова для определения соответствия
    coverage_patterns = {
        "ассортимент": ["футболк", "платье", "брюки", "юбк", "блузк", "пижам", "костюм", "свитер"],
        "тираж": ["штук", "единиц", "тысяч", "сотен", "много", "мало", "тираж"],
        "бюджет": ["рубл", "тысяч", "бюджет", "стоимость", "цена", "дорого", "дешево"],
        "сроки": ["недел", "месяц", "срочно", "быстро", "когда", "сроки", "время"],
    }
    
    for topic, keywords in coverage_patterns.items():
        if topic in question_lower:
            if any(keyword in user_lower for keyword in keywords):
                return True
    
    return False


async def notify_managers(update: Update, lead_info: dict) -> None:
    """Уведомление менеджеров о новом лиде"""
    try:
        user = update.effective_user
        message = (
            f"🧵 Новый лид готов к обработке!\n"
            f"👤 Пользователь: @{user.username or user.first_name} (ID: {user.id})\n"
            f"📌 Собранная информация:\n\n"
        )
        
        for question, answer in lead_info.items():
            message += f"• {question}\n  ➜ {answer}\n\n"

        logger.info(f"📨 Уведомление менеджерам:\n{message}")
        
        # Здесь можно добавить отправку в CRM, email, Telegram-группу менеджеров
        
    except Exception as e:
        logger.error(f"❌ Ошибка в notify_managers: {e}")


async def main() -> None:
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN не найден в окружении")
        return
    
    # Создаем persistence для сохранения состояний
    persistence_file = os.path.expanduser("~/ai_seller/project/bot_data.pkl")
    persistence = PicklePersistence(filepath=persistence_file)
    
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).persistence(persistence).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🎯 Запуск Telegram бота с сохранением состояний...")
    await app.run_polling()


if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    logger.info("🔄 Запуск Telegram бота...")
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⏳ Завершение работы...")