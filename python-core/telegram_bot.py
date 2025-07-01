# ~/ai_seller/project/python-core/telegram_bot.py

import os
import asyncio
import logging

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from dialog.flow_manager import FlowManager
from llm.orchestrator import LLMOrchestrator
from dialog.state_machine import FSMFactory
from dialog.context import RedisSessionStore
from bot.handlers import register_handlers

# Загружаем переменные окружения из .env
load_dotenv()

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Читаем переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TENANT_ID = os.getenv("TENANT_ID", "default")

if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не найден в окружении!")
    exit(1)

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Инициализация зависимостей FlowManager
orchestrator = LLMOrchestrator()
fsm_factory = FSMFactory()
session_store = RedisSessionStore(REDIS_URL)

flow_manager = FlowManager(
    orchestrator=orchestrator,
    fsm_factory=fsm_factory,
    tenant_id=TENANT_ID,
    session_store=session_store,
)

# Регистрация хендлеров с передачей flow_manager и tenant_id
register_handlers(dp, flow_manager, TENANT_ID)


async def main():
    logger.info("🚀 SoVAni Telegram bot запущен.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
