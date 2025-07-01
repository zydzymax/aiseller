"""
FSM для диалога AI-продавца SoVAni.
Включает валидацию, гибкие переходы, извлечение полей из свободного 
текста, возможность возврата и интеграцию с CRM/аналитикой.
"""

from enum import Enum
from typing import Optional, Dict, List, Callable, Tuple
import re
from datetime import datetime
from dataclasses import dataclass, field

class Stage(str, Enum):
    WELCOME = "welcome"
    PRODUCT_TYPE = "product_type"
    FABRIC = "fabric"
    QUANTITY = "quantity"
    DEADLINE = "deadline"
    CONTACTS = "contacts"
    COMPLETED = "completed"

@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    meta: Dict = field(default_factory=dict)

class Validators:
    @staticmethod
    def validate_quantity(value: str) -> Tuple[bool, Optional[str]]:
        match = re.match(r"\d+", value.replace(" ", ""))
        if not match:
            return False, "Пожалуйста, укажите количество цифрами."
        qty = int(match.group())
        if qty < 30:
            return False, "Минимальный тираж — 30 штук."
        if qty > 10000:
            return False, "Для крупных заказов уточните у менеджера."
        return True, str(qty)

    @staticmethod
    def validate_contacts(value: str) -> Tuple[bool, Optional[str]]:
        if "@" in value or value.startswith("+") or re.match(r"\d{10,}", value):
            return True, value.strip()
        return False, "Пожалуйста, оставьте Telegram или номер телефона."

    @staticmethod
    def validate_field(field: str, value: str) -> Tuple[bool, 
Optional[str]]:
        validators = {
            "quantity": Validators.validate_quantity,
            "contacts": Validators.validate_contacts,
            # Можно добавить и для других полей
        }
        if field in validators:
            return validators[field](value)
        return True, value.strip()

class DataExtractor:
    @staticmethod
    def extract_all_data(text: str) -> Dict[str, str]:
        # Очень простые шаблоны, можно улучшить
        result = {}
        qty = re.search(r"(\d{2,5})\s*(шт|штук|единиц|партия)?", text, re.I)
        if qty:
            result["quantity"] = qty.group(1)
        phone = re.search(r"((?:\+7|8)\d{10}|\d{10})", text)
        if phone:
            result["contacts"] = phone.group(1)
        # Fabric and product type
        for fabric in ["футер", "кулирка", "интерлок", "рибана", "хлопок"]:
            if fabric in text.lower():
                result["fabric"] = fabric
        for product in ["пижам", "футболк", "брюк", "костюм"]:
            if product in text.lower():
                result["product_type"] = product
        # Deadline
        for word in ["срочно", "недел", "месяц", "дня", "дней"]:
            if word in text.lower():
                result["deadline"] = text
        return result

class DialogState:
    def __init__(self, user_id: Optional[int] = None):
        self.user_id = user_id
        self.stage: Stage = Stage.WELCOME
        self.data: Dict[str, Optional[str]] = {
            "product_type": None,
            "fabric": None,
            "quantity": None,
            "deadline": None,
            "contacts": None,
        }
        self.history: List[Message] = []
        self.previous_stages: List[Stage] = []
        self.validation_errors: Dict[str, str] = {}

    def go_back(self) -> bool:
        if self.previous_stages:
            self.stage = self.previous_stages.pop()
            return True
        return False

    def add_message(self, role: str, content: str, meta: Dict = None):
        self.history.append(Message(role=role, content=content, meta=meta or {}))

    def _get_current_field(self) -> Optional[str]:
        order = ["product_type", "fabric", "quantity", "deadline", "contacts"]
        for f in order:
            if not self.data[f]:
                return f
        return None

    def update_data(self, field: str, value: str) -> Tuple[bool, Optional[str]]:
        # Валидация
        is_valid, val_or_err = Validators.validate_field(field, value)
        if not is_valid:
            self.validation_errors[field] = val_or_err
            return False, val_or_err
        self.data[field] = val_or_err
        self.validation_errors.pop(field, None)
        # Продвинуть стадию
        self._auto_transition()
        return True, None

    def _auto_transition(self):
        # Продвигаем стадию, если поле заполнено
        order = [
            (Stage.PRODUCT_TYPE, "product_type"),
            (Stage.FABRIC, "fabric"),
            (Stage.QUANTITY, "quantity"),
            (Stage.DEADLINE, "deadline"),
            (Stage.CONTACTS, "contacts"),
        ]
        for stg, field in order:
            if self.stage == stg and self.data[field]:
                self.previous_stages.append(self.stage)
                self.stage = Stage(order[order.index((stg, field)) + 1][0]) \
                    if order.index((stg, field)) + 1 < len(order) else Stage.COMPLETED

    def process_message(self, message: str) -> Dict:
        self.add_message('user', message)
        extracted = DataExtractor.extract_all_data(message)
        for field, value in extracted.items():
            self.update_data(field, value)
        # Если ни одно поле не извлечено, обновляем текущее
        if not extracted:
            current = self._get_current_field()
            if current:
                self.update_data(current, message)
        # Генерируем вопрос/ошибку/финал
        if self.validation_errors:
            err_field, err_text = next(iter(self.validation_errors.items()))
            return {"response": err_text, "stage": self.stage.value, "is_complete": False, "data": self.data}
        if self.is_complete():
            return {"response": self._summary(), "stage": self.stage.value, "is_complete": True, "data": self.data}
        return {"response": self.get_next_question(), "stage": self.stage.value, "is_complete": False, "data": self.data}

    def get_next_question(self) -> Optional[str]:
        questions = {
            Stage.WELCOME: "Здравствуйте! Давайте рассчитаем заказ. Что именно хотите пошить? (футболки, пижамы, брюки...)",
            Stage.PRODUCT_TYPE: "Какой именно ассортимент интересует?",
            Stage.FABRIC: "Из какой ткани предпочтительнее шить?",
            Stage.QUANTITY: "Какой примерный тираж нужен?",
            Stage.DEADLINE: "В какие сроки нужен заказ?",
            Stage.CONTACTS: "Ваш телефон или Telegram для связи менеджера?",
        }
        return questions.get(self.stage)

    def is_complete(self) -> bool:
        return all(self.data.values()) and self.stage == Stage.COMPLETED

    def _summary(self) -> str:
        return (
            f"Отлично, вот что я записала:\n"
            f"— Изделие: {self.data['product_type']}\n"
            f"— Ткань: {self.data['fabric']}\n"
            f"— Тираж: {self.data['quantity']} шт\n"
            f"— Сроки: {self.data['deadline']}\n"
            f"— Контакт: {self.data['contacts']}\n"
            "Менеджер свяжется для уточнения деталей. Спасибо!"
        )

