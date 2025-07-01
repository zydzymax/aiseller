# ~/ai_seller/project/python-core/objection_handler.py

"""
Модуль обработки клиентских возражений.
Обеспечивает классификацию и генерацию ответов на частые возражения 
(дорого, не сейчас, уже есть поставщик и т.д.)
"""

import json
import os
from typing import Dict, Optional


class ObjectionHandler:
    """
    Класс для обработки возражений клиента с использованием шаблонов.
    """

    def __init__(self, library_path: str = 
"python-core/config/objections_library.json"):
        """
        Загружает библиотеку возражений и ответов.

        :param library_path: Путь до JSON с шаблонами
        """
        self.library_path = library_path
        self.objections = self._load_library()

    def _load_library(self) -> Dict[str, Dict[str, str]]:
        """
        Загружает шаблоны возражений и ответов.

        :return: Словарь вида {тип_возражения: {description, response, 
tone}}
        """
        if not os.path.exists(self.library_path):
            raise FileNotFoundError(f"Файл возражений не найден: 
{self.library_path}")
        try:
            with open(self.library_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка чтения библиотеки возражений: {e}")

    def classify_objection(self, text: str) -> Optional[str]:
        """
        Наивная классификация фразы по ключевым словам (будет улучшено ML 
позже)

        :param text: Текст возражения клиента
        :return: Ключ шаблона или None
        """
        text = text.lower()
        if "дорог" in text or "цена" in text:
            return "price"
        elif "долго" in text or "срок" in text:
            return "time"
        elif "уже есть" in text or "работаем с другим" in text:
            return "have_supplier"
        elif "неинтересно" in text or "не нужно" in text:
            return "not_interested"
        else:
            return None

    def get_response(self, objection_key: str) -> Optional[str]:
        """
        Получить ответ по ключу возражения.

        :param objection_key: Ключ из шаблона
        :return: Текст ответа
        """
        entry = self.objections.get(objection_key)
        if entry:
            return entry.get("response")
        return None


# Пример локального использования
if __name__ == "__main__":
    handler = ObjectionHandler()
    example = "Сейчас неинтересно, у нас уже есть поставщик"
    key = handler.classify_objection(example)
    print(f"Классифицировано как: {key}")
    if key:
        print("Ответ:", handler.get_response(key))

