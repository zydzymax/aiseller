from llm_logic import generate_response
from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env")

# Тестовый запрос к GPT-4
response = generate_response(
    prompt="Сделай короткий, тёплый ответ на отзыв: 'Пижама понравилась, спасибо!'",
    system_prompt="Ты — заботливый AI-помощник бренда Sovani. Отвечай дружелюбно, с благодарностью и лёгким обаянием."
)

print("Ответ GPT-4:\n", response)

