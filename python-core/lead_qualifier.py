# ~/ai_seller/project/python-core/lead_qualifier.py

"""
Модуль для квалификации лидов на основе ответов клиента.
Определяет готовность к сделке: холодный, тёплый или горячий лид.
"""

from typing import Dict, Literal, Optional

LeadStatus = Literal["cold", "warm", "hot"]


class LeadQualifier:
    """
    Класс оценки лида на основе простых критериев.
    """

    def __init__(self):
        """
        Инициализация порогов квалификации.
        Можно адаптировать под бизнес-логику.
        """
        self.thresholds = {
            "hot": 4,
            "warm": 2
        }

    def score_lead(self, answers: Dict[str, Optional[str]]) -> int:
        """
        Присваивает баллы в зависимости от полноты и уверенности ответов.

        :param answers: Ответы клиента (ключи: budget, timeframe, 
decision, interest, contact_ready)
        :return: Общий балл
        """
        score = 0

        if answers.get("budget"):
            score += 1
        if answers.get("timeframe"):
            score += 1
        if answers.get("decision") in {"сам", "ЛПР", "директор"}:
            score += 1
        if answers.get("interest") in {"да", "хочу", "расскажите"}:
            score += 1
        if answers.get("contact_ready") in {"да", "можно", "пишите"}:
            score += 1

        return score

    def qualify(self, answers: Dict[str, Optional[str]]) -> LeadStatus:
        """
        Присваивает лиду статус воронки.

        :param answers: Ответы клиента
        :return: Статус: "cold", "warm" или "hot"
        """
        score = self.score_lead(answers)
        if score >= self.thresholds["hot"]:
            return "hot"
        elif score >= self.thresholds["warm"]:
            return "warm"
        return "cold"


# Пример локального использования
if __name__ == "__main__":
    qualifier = LeadQualifier()

    test_answers = {
        "budget": "500000",
        "timeframe": "в этом месяце",
        "decision": "директор",
        "interest": "да",
        "contact_ready": "да"
    }

    score = qualifier.score_lead(test_answers)
    status = qualifier.qualify(test_answers)

    print(f"Сумма баллов: {score}")
    print(f"Квалификация: {status}")

