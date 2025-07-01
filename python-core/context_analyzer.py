# ~/ai_seller/project/python-core/context_analyzer.py

"""
Модуль анализа сообщений клиента.
Определяет намерения, ключевые сигналы и предполагаемую стадию воронки.
"""

from typing import Dict, Literal, Optional


Intent = Literal["interest", "question", "objection", "rejection", 
"greeting", "farewell", "unclear"]
Stage = Literal[
    "greeting", "persona_intro", "need_identification", "product_pitch",
    "objection_handling", "lead_qualification", "closing", "farewell"
]


class ContextAnalyzer:
    """
    Класс для анализа входящих сообщений клиента.
    """

    def __init__(self):
        # Ключевые сигналы для наивной классификации (можно вынести в 
конфиг)
        self.intent_keywords = {
            "greeting": ["привет", "здравствуйте", "добрый"],
            "farewell": ["спасибо", "пока", "всего доброго"],
            "interest": ["интересует", "хочу", "расскажите", "пришлите", 
"давайте"],
            "question": ["что", "как", "где", "сколько", "какие", "?"],
            "objection": ["дорого", "долго", "уже есть", "не нужно", "не 
подходит"],
            "rejection": ["неинтересно", "откажусь", "не надо"]
        }

    def detect_intent(self, text: str) -> Intent:
        """
        Наивное определение намерения клиента.

        :param text: Входящее сообщение
        :return: Тип намерения
        """
        text = text.lower()
        for intent, keywords in self.intent_keywords.items():
            if any(keyword in text for keyword in keywords):
                return intent  # type: ignore
        return "unclear"

    def predict_stage(self, intent: Intent) -> Stage:
        """
        Примерное сопоставление намерения стадии воронки.

        :param intent: Определённый тип намерения
        :return: Предположительная стадия диалога
        """
        mapping = {
            "greeting": "greeting",
            "interest": "need_identification",
            "question": "product_pitch",
            "objection": "objection_handling",
            "rejection": "farewell",
            "farewell": "farewell"
        }
        return mapping.get(intent, "need_identification")

    def analyze(self, text: str) -> Dict[str, str]:
        """
        Главная точка входа: возвращает и намерение, и стадию.

        :param text: Входящее сообщение
        :return: Словарь с 'intent' и 'stage'
        """
        intent = self.detect_intent(text)
        stage = self.predict_stage(intent)
        return {
            "intent": intent,
            "stage": stage
        }


# Пример использования
if __name__ == "__main__":
    analyzer = ContextAnalyzer()
    msg = "Здравствуйте, подскажите по срокам и цене"
    result = analyzer.analyze(msg)
    print("Намерение:", result["intent"])
    print("Предположительная стадия:", result["stage"])

