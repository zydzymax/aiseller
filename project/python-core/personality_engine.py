# ~/ai_seller/project/python-core/personality_engine.py

"""
Модуль генерации персон для AI-продавца.
Персона определяет стиль общения, характер, мотивацию и словарь, 
адаптированный под клиента.
"""

import json
from typing import Dict, Optional
import os


class PersonalityEngine:
    """
    Генератор персон на основе шаблонов и контекста пользователя.
    """

    def __init__(self, config_path: str = 
"python-core/config/personality_templates.json"):
        """
        Загружает JSON-файл с шаблонами персон.

        :param config_path: Путь до JSON-файла с шаблонами персон
        """
        self.config_path = config_path
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, Dict]:
        """
        Загружает шаблоны персон из JSON.

        :return: Словарь шаблонов персон
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Файл шаблонов не найден: 
{self.config_path}")
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга шаблонов персон: {e}")

    def generate_persona(self, segment: str, tone: Optional[str] = None) 
-> Dict[str, str]:
        """
        Генерирует описание персонажа по сегменту и желаемому тону.

        :param segment: Сегмент клиента (например, 'b2b', 'мамы', 
'поставщики', 'салоны красоты')
        :param tone: Необязательный тон общения (мягкий, деловой, 
экспертный и т.д.)
        :return: Словарь с персоной: имя, голос, мотивация, стиль, фразы
        """
        template = self.templates.get(segment.lower())
        if not template:
            raise ValueError(f"Шаблон не найден для сегмента: {segment}")

        persona = template.copy()

        if tone:
            persona["tone"] = tone
            # Можно менять стиль речи в зависимости от тона
            if tone == "мягкий":
                persona["style"] = "доброжелательный, поддерживающий"
            elif tone == "деловой":
                persona["style"] = "корректный, уверенный"
            elif tone == "экспертный":
                persona["style"] = "уверенный, объясняющий, с примерами"

        return persona


# Пример локального запуска
if __name__ == "__main__":
    engine = PersonalityEngine()
    try:
        persona = engine.generate_persona(segment="b2b", tone="деловой")
        print("Сгенерированная персона:\n", json.dumps(persona, indent=2, 
ensure_ascii=False))
    except Exception as e:
        print(f"Ошибка генерации: {e}")

