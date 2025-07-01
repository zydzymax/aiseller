import logging
from aiogram import types, Dispatcher
from aiogram.types import Message
from opentelemetry import trace

from utils.input_sanitizer import sanitize_input
from dialog.flow_manager import FlowManager

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("telegram.handler")

async def handle_message(
    message: Message, 
    flow_manager: FlowManager,
    tenant_id: str
):
    user_id = str(message.from_user.id)
    text = message.text or ""
    
    with tracer.start_as_current_span("handle_message") as span:
        span.set_attributes({
            "user.id": user_id,
            "message.length": len(text),
            "tenant.id": tenant_id
        })
        
        try:
            clean_text = sanitize_input(text[:2000])
            
            logger.info(
                f"Message received",
                extra={
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "message": clean_text[:100]
                }
            )
            
            if clean_text.startswith("/"):
                await handle_command(message, clean_text)
                return
                
            await message.bot.send_chat_action(message.chat.id, "typing")
            
            response = await flow_manager.process_input(
                user_id=user_id,
                user_text=clean_text,
                metadata={
                    "chat_id": message.chat.id,
                    "message_id": message.message_id,
                    "platform": "telegram"
                }
            )
            
            await send_response(message, response)
            
        except Exception as e:
            logger.exception(
                "Message processing failed",
                extra={"user_id": user_id, "error": str(e)}
            )
            span.record_exception(e)
            await handle_error(message)

async def handle_command(message: Message, command: str):
    command = command.lower().split()[0]
    commands = {
        "/start": "👋 Добро пожаловать в Sovani AI! Я помогу с расчетами заказов. Просто опишите, что вам нужно.",
        "/help": "ℹ️ Я AI-продавец SoVAni. Задавайте вопросы о пошиве, материалах и сроках. Пример: «Сколько стоит 100 халатов из хлопка?»",
        "/reset": "🔄 Ваша сессия сброшена. Начнем заново!",
    }
    response = commands.get(command, "⚠️ Неизвестная команда. Используйте /help для справки.")
    await message.answer(response)

async def send_response(message: Message, response: dict):
    if response.get("error"):
        await message.answer("⚠️ Произошла ошибка обработки. Попробуйте позже.")
        return
        
    fsm = response.get("fsm", {})
    llm = response.get("llm", {})
    
    if llm and llm.get("content"):
        await message.answer(llm["content"])
    elif fsm and fsm.get("response"):
        await message.answer(fsm["response"])
    else:
        await message.answer("🤔 Я не совсем понял запрос. Можете переформулировать?")

async def handle_error(message: Message):
    await message.answer(
        "🚫 Произошла непредвиденная ошибка. Наши инженеры уже работают над исправлением. "
        "Попробуйте повторить запрос через пару минут."
    )

def register_handlers(dp: Dispatcher, flow_manager: FlowManager, tenant_id: str):
    dp.register_message_handler(
        lambda m: handle_message(m, flow_manager, tenant_id),
        content_types=types.ContentType.TEXT
    )
    from .middleware import AntiFloodMiddleware
    dp.middleware.setup(AntiFloodMiddleware(limit=1.0))
