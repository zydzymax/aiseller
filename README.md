# 🤖 SoVAni AI-продавец — Telegram-бот для автоматизации B2B-продаж

![GitHub repo size](https://img.shields.io/github/repo-size/your-username/sovani-ai-seller)
![Made with Go & Python](https://img.shields.io/badge/stack-Go%20%26%20Python-green)
![License](https://img.shields.io/github/license/your-username/sovani-ai-seller)

---

**SoVAni AI-продавец** — это интеллектуальный Telegram-бот, выступающий в роли тёплого и профессионального менеджера швейной фабрики. Он ведёт клиентов через воронку продаж, понимает эмоции, адаптирует стиль общения, собирает данные для просчёта партии и уведомляет команду.

## 📌 Основные возможности

- 💬 Общается от лица менеджера Лены (SoVAni)
- 🧠 Понимает эмоции клиента через Claude Sonnet 4
- 🗂 Задаёт вопросы по одному, ведёт диалог пошагово
- 🤖 Использует OpenAI / Claude / Yandex STT-TTS
- 📈 Сохраняет историю общения и собирает данные лида
- 🔗 Уведомляет CRM / менеджеров при завершении диалога
- 🧵 Учитывает тип клиента: холодный, возвращённый, новый
- 📦 Масштабируемая архитектура (Go + Python)

## 🏗 Архитектура

### Backend (Go)
- `go-api/main.go`: точка входа API
- `handlers/telegram.go`: вебхуки Telegram
- `dialog/manager.go`: маршрутизация и вызов LLM
- `storage/pg.go`: PostgreSQL
- `storage/redis.go`: Redis
- `jobs/worker.go`: обработка очередей
- `dashboard/dashboard.go`: мониторинг

### Core (Python)
- `telegram_bot.py`: логика Telegram-бота
- `llm_logic.py`: генерация ответов через OpenAI
- `claude_emotion.py`: адаптация тональности через Claude
- `conversation_flow.py`: логика воронки
- `personality_engine.py`: генерация персон
- `config/*.json`: скрипты, шаблоны, возражения, эмоции

## 🚀 Быстрый запуск (для локальной разработки)

```bash
git clone https://github.com/your-username/sovani-ai-seller.git
cd sovani-ai-seller
cp .env.example .env
# заполни TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, ANTHROPIC_API_KEY и другие
docker-compose up --build
```

### 🛠 Стек технологий

- `Go 1.22+` — API и обработка вебхуков
- `Python 3.11+` — логика бота и LLM-интеграции
- `Redis`, `PostgreSQL` — хранение состояний и данных
- `Docker` / `Makefile` — инфраструктура и деплой

## 🧩 Интеграции

| Сервис         | Назначение                          |
|----------------|-------------------------------------|
| Telegram Bot API | Входящий/исходящий канал общения  |
| OpenAI GPT-4    | Генерация логики диалога            |
| Claude Sonnet   | Эмоциональная адаптация ответов     |
| Yandex SpeechKit| Озвучка и распознавание голоса      |
| Redis, Postgres | Хранение, кэширование               |

## 📂 Структура проекта

```
project/
├── go-api/                # Go-сервер
├── python-core/           # Python-логика
├── scripts/               # Bash и миграции
├── deployments/           # Docker и nginx
├── saas/                  # SaaS инфраструктура
├── tests/                 # Unit + интеграционные тесты
└── docs/                  # Документация и API
```

## 📣 Автор

Проект разработан командой швейной фабрики [SoVAni](https://t.me/sovani_factory) для автоматизации B2B-продаж на маркетплейсах и через прямые обращения в мессенджерах.

## 📝 Лицензия

Проект доступен под лицензией MIT. См. файл [LICENSE](LICENSE).

---

### 🤝 Готовы к сотрудничеству

Ищем партнёров для пилотного внедрения в сфере B2B продаж, маркетплейсов, текстиля и AI-автоматизации.  
Пиши 👉 [WhatsApp](https://api.whatsapp.com/send/?phone=79938931692)