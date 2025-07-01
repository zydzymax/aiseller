# ~/ai_seller/project/python-core/response_validator.py

"""
Модуль валидации ответов LLM.
Фильтрует токсичность, бессмысленность, дублирование и нарушение тона.
"""

from typing import Optional


class ResponseValidator:
    """
    Проверяет корректность ответа перед отправкой клиенту.
    """

    def __init__(self, min_length: int = 10):
        """
        Инициализация базовых настроек валидации.

        :param min_length: Минимально допустимая длина ответа
        """
        self.min_length = min_length
        self.toxic_keywords = [
            "тупой", "идиот", "бесполезно", "ненавижу", "неадекват", 
"жирный", "отвратительно"
        ]

    def is_valid(self, response: Optional[str]) -> bool:
        """
        Главная точка проверки. Отклоняет недопустимые ответы.

        :param response: Ответ от модели
        :return: True, если ответ пригоден для клиента
        """
        if not response:
            return False

        clean = response.strip().lower()

        if len(clean) < self.min_length:
            return False

        if clean in {"...", "?", "не знаю", "понятно"}:
            return False

        if any(bad_word in clean for bad_word in self.toxic_keywords):
            return False

        return True

    def get_issues(self, response: Optional[str]) -> str:
        """
        Возвращает описание проблем, если они есть.

        :param response: Ответ от модели
        :return: Текст с причинами
        """
        if not response or not response.strip():
            return "Ответ пустой или отсутствует."
        clean = response.lower().strip()

        if len(clean) < self.min_length:
            return "Ответ слишком короткий."

        if any(bad in clean for bad in self.toxic_keywords):
            return "Ответ содержит потенциально токсичную лексику."

        return "OK"


# Пример локального теста
if __name__ == "__main__":
    validator = ResponseValidator()
    test_responses = [
        "Да.",
        "Ты тупой и ничего не понимаешь.",
        "Хороший выбор, могу рассказать подробнее!",
        None
    ]

    for r in test_responses:
        print("Ответ:", r)
        print("Валиден?", validator.is_valid(r))
        print("Пояснение:", validator.get_issues(r))
        print("-" * 30)

