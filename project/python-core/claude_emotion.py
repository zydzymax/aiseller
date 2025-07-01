import os
import httpx
import logging
from typing import Tuple, Optional
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv(dotenv_path=os.path.expanduser("~/ai_seller/project/.env"))
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


def analyze_emotion(text: str) -> Tuple[str, float]:
    """Анализирует эмоцию в тексте клиента"""
    if not text or not text.strip():
        return "нейтральное", 0.5

    text_lower = text.lower().strip()
    
    # Упрощенные паттерны для базовой классификации
    patterns = {
        "негатив": ["не хочу", "не нужно", "не буду", "отказываюсь", "плохо", 
                    "ужасно", "не нравится", "не подходит", "разочарован",
                    "не покупаю", "не интересно", "отвратительно", "кошмар", "дорого"],
        "сомнение": ["не уверен", "сомневаюсь", "не устраивает", "думаю", 
                     "возможно", "не знаю", "переживаю", "боюсь", "а вдруг", 
                     "стоит ли", "надо подумать", "может быть"],
        "интерес": ["интересно", "хочу", "нужно", "подойдет", "нравится",
                    "отлично", "хорошо", "классно", "супер", "да", "здорово",
                    "согласен", "буду покупать", "заказываю", "понравилось"],
        "вопрос": ["как", "что", "где", "когда", "почему", "сколько", "можно ли", "?"],
        "приветствие": ["привет", "здравствуйте", "добрый день", "добрый вечер", 
                        "доброе утро", "hi", "hello", "салют"]
    }
    
    scores = {}
    for emotion, words in patterns.items():
        # Для вопросов учитываем знак вопроса отдельно
        if emotion == "вопрос":
            score = sum(1 for word in words if word in text_lower)
            if "?" in text:
                score += 2
        else:
            score = sum(1 for word in words if word in text_lower)
        
        if score > 0:
            scores[emotion] = score
    
    if not scores:
        return "нейтральное", 0.5
    
    # Находим доминирующую эмоцию
    dominant_emotion = max(scores.items(), key=lambda x: x[1])
    confidence = min(0.95, 0.6 + dominant_emotion[1] * 0.1)
    
    return dominant_emotion[0], confidence


def get_emotional_adaptation(emotion: str, confidence: float) -> str:
    """Возвращает инструкцию для адаптации тона ответа"""
    adaptations = {
        "негатив": "Используй мягкий, понимающий тон. Не давай, а предложи помощь.",
        "сомнение": "Будь уверенной и поддерживающей. Дай конкретные факты.",
        "интерес": "Поддержи энтузиазм, но не переусердствуй. Веди к действию.",
        "вопрос": "Отвечай прямо и информативно, без лишних слов.",
        "приветствие": "Отвечай тепло и дружелюбно, как знакомому человеку.",
        "нейтральное": "Используй профессиональный, но дружелюбный тон."
    }
    return adaptations.get(emotion, adaptations["нейтральное"])


def humanize_reply(text: str, system_prompt: str = "", client_message: str = "") -> str:
    """Адаптирует ответ с учетом эмоции клиента через Claude"""
    try:
        if not ANTHROPIC_API_KEY:
            logger.error("ANTHROPIC_API_KEY не найден в переменных окружения")
            return text

        # Анализируем эмоцию только если есть сообщение клиента
        emotion = "нейтральное"
        if client_message and client_message.strip():
            emotion, confidence = analyze_emotion(client_message)
            logger.info(f"Эмоция клиента: {emotion} (уверенность: {confidence:.2f})")

        # Формируем системный промпт для адаптации
        emotional_guidance = get_emotional_adaptation(emotion, 0.7)
        
        adaptation_prompt = (
            "Ты Лена, менеджер швейной фабрики SoVAni. "
            "Адаптируй следующий текст под настроение клиента.\n\n"
            f"Настроение клиента: {emotion}\n"
            f"Как адаптировать: {emotional_guidance}\n\n"
            "ВАЖНО: Выдай только адаптированный текст, без объяснений и комментариев. "
            "Сохрани смысл, но подстрой тон под эмоцию."
        )

        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 400,
            "temperature": 0.4,  # Снижаем для более предсказуемых ответов
            "system": adaptation_prompt,
            "messages": [
                {
                    "role": "user", 
                    "content": text.strip()
                }
            ]
        }

        headers = {
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        with httpx.Client(timeout=25.0) as client:
            response = client.post("https://api.anthropic.com/v1/messages", 
                                 headers=headers, json=payload)
            response.raise_for_status()

        data = response.json()
        content = data.get("content", [])
        
        if isinstance(content, list) and content and content[0].get("text"):
            adapted_text = content[0]["text"].strip()
            logger.info(f"Текст адаптирован для эмоции: {emotion}")
            return adapted_text
        
        return text
        
    except httpx.TimeoutException:
        logger.error("Таймаут при обращении к Claude API")
        return text
    except httpx.HTTPError as e:
        logger.error(f"HTTP ошибка при обращении к Claude: {e}")
        return text
    except Exception as e:
        logger.error(f"Неожиданная ошибка в humanize_reply: {e}")
        return text


def process_conversation(client_message: str, bot_response: str) -> str:
    """Основная функция для обработки диалога"""
    try:
        if not client_message or not bot_response:
            return bot_response
            
        return humanize_reply(text=bot_response, client_message=client_message)
    except Exception as e:
        logger.error(f"Ошибка в process_conversation: {e}")
        return bot_response


def test_emotions():
    """Тестирование определения эмоций"""
    test_cases = [
        ("Привет", "приветствие"),
        ("Ваши цены просто ужасные, не буду покупать!", "негатив"),
        ("Сколько стоит пошив платья на заказ?", "вопрос"),
        ("Не уверен, что мне это подойдет...", "сомнение"),
        ("Отлично! Мне очень нравится ваша работа!", "интерес"),
        ("Думаю, это слишком дорого для меня", "сомнение"),
        ("Здравствуйте", "приветствие"),
        ("Нужно платье на свадьбу", "нейтральное")
    ]
    
    print("=== Тест распознавания эмоций ===")
    for message, expected in test_cases:
        emotion, confidence = analyze_emotion(message)
        status = "✅" if emotion == expected else "❌"
        print(f"{status} '{message}' -> {emotion} ({confidence:.2f}) [ожидалось: {expected}]")


if __name__ == "__main__":
    test_emotions()