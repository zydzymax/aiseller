# ~/ai_seller/project/python-core/conversation_flow.py

"""
Модуль управления стадиями диалога AI-продавца.
Обеспечивает переходы между шагами, отслеживает текущую фазу и логику 
следующего действия.
"""

from typing import Dict, Optional


class ConversationFlow:
    """
    Класс управления стадиями диалога с клиентом.
    """

    STAGES = [
        "greeting",
        "persona_intro",
        "need_identification",
        "product_pitch",
        "objection_handling",
        "lead_qualification",
        "closing",
        "farewell"
    ]

    def __init__(self):
        """
        Инициализация диалога с начальной стадией.
        """
        self.current_stage = "greeting"
        self.history = []

    def advance(self) -> Optional[str]:
        """
        Переход к следующей стадии диалога.

        :return: Новая стадия или None, если диалог завершён
        """
        try:
            current_index = self.STAGES.index(self.current_stage)
            if current_index + 1 < len(self.STAGES):
                self.current_stage = self.STAGES[current_index + 1]
                self.history.append(self.current_stage)
                return self.current_stage
            else:
                return None  # Диалог завершён
        except ValueError:
            return None  # Неизвестная стадия

    def set_stage(self, stage: str) -> bool:
        """
        Принудительно задать текущую стадию.

        :param stage: Название стадии
        :return: Успешность установки
        """
        if stage in self.STAGES:
            self.current_stage = stage
            self.history.append(stage)
            return True
        return False

    def is_stage(self, stage: str) -> bool:
        """
        Проверка текущей стадии.

        :param stage: Название стадии
        :return: True, если стадия совпадает
        """
        return self.current_stage == stage

    def get_current_stage(self) -> str:
        """
        Получить текущую активную стадию диалога.

        :return: Название стадии
        """
        return self.current_stage

    def reset(self) -> None:
        """
        Сбросить диалог к начальной стадии.

        :return: None
        """
        self.current_stage = "greeting"
        self.history.clear()


# Пример тестового использования
if __name__ == "__main__":
    flow = ConversationFlow()
    print("Текущая стадия:", flow.get_current_stage())
    while flow.advance():
        print("Следующая стадия:", flow.get_current_stage())

