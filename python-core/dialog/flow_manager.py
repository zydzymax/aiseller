"""
flow_manager.py

Интеграционный модуль между FSM, Orchestrator, input_sanitizer и сессией.
Использует Redis для хранения сессий (async), поддерживает хуки, обработку ошибок и multi-tenancy.
"""

import logging
import asyncio
import pickle
from typing import Dict, Any, Optional, Callable, List
from llm.orchestrator import LLMOrchestrator
from dialog.state_machine import DialogState
from utils.input_sanitizer import sanitize_input
from redis.asyncio import Redis
from opentelemetry import trace

logger = logging.getLogger("dialog.flow_manager")

class RedisSessionStore:
    def __init__(self, redis_url: str, ttl: int = 3600):
        self.redis = Redis.from_url(redis_url)
        self.ttl = ttl

    async def get(self, user_id: str) -> Optional[DialogState]:
        data = await self.redis.get(f"sessions:{user_id}")
        return pickle.loads(data) if data else None

    async def set(self, user_id: str, state: DialogState):
        await self.redis.setex(f"sessions:{user_id}", self.ttl, pickle.dumps(state))

    async def cleanup(self):
        pass

class FlowManager:
    def __init__(
        self,
        orchestrator: LLMOrchestrator,
        fsm_factory: Callable[[], DialogState],
        tenant_id: str,
        session_store: RedisSessionStore,
        input_sanitizer: Callable[[str], str] = sanitize_input,
        hooks: Optional[Dict[str, List[Callable]]] = None
    ):
        self.orchestrator = orchestrator
        self.fsm_factory = fsm_factory
        self.tenant_id = tenant_id
        self.session_store = session_store
        self.input_sanitizer = input_sanitizer
        self.hooks = hooks or {}

    async def get_state(self, user_id: str) -> DialogState:
        state = await self.session_store.get(user_id)
        if not state:
            state = self.fsm_factory()
            await self.session_store.set(user_id, state)
        return state

    async def _trigger_hook(self, hook_name: str, *args, **kwargs):
        for hook in self.hooks.get(hook_name, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(*args, **kwargs)
                else:
                    hook(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook {hook_name} failed: {e}")

    async def process_input(self, user_id: str, user_text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        tracer = trace.get_tracer("flow_manager")
        with tracer.start_as_current_span("process_input") as span:
            span.set_attributes({
                "user.id": user_id,
                "tenant.id": self.tenant_id,
                "input.length": len(user_text)
            })
            try:
                await self._trigger_hook("pre_process", user_id, user_text)
                safe_text = self.input_sanitizer(user_text[:2000])
                state = await self.get_state(user_id)
                if hasattr(state, "process_message_async"):
                    fsm_result = await state.process_message_async(safe_text)
                else:
                    fsm_result = state.process_message(safe_text)
                await self.session_store.set(user_id, state)
                if fsm_result.get("is_complete"):
                    llm_request = self._build_llm_request(state, user_text, metadata)
                    llm_response = await self.orchestrator.generate(
                        request=llm_request,
                        tenant_id=self.tenant_id,
                        user_id=user_id
                    )
                    await self._trigger_hook("post_process", user_id, llm_response)
                    span.set_attribute("response.type", "llm")
                    return {"fsm": fsm_result, "llm": llm_response.__dict__}
                span.set_attribute("response.type", "fsm")
                return {"fsm": fsm_result, "llm": None}
            except Exception as e:
                logger.exception("Unhandled flow error")
                await self._trigger_hook("error", user_id, e)
                return {"error": "internal_error", "details": str(e)}

    def _build_llm_request(self, state: DialogState, user_text: str, metadata: Optional[Dict[str, Any]]) -> Any:
        from llm.base import LLMRequest, ModelType
        llm_config = getattr(state, "get_llm_config", lambda: {})()
        return LLMRequest(
            prompt=state._summary(),
            model=llm_config.get("model", ModelType.GPT_4_TURBO),
            history=[{"role": "user", "content": user_text}],
            system_prompt=llm_config.get("system_prompt", "Ты AI-продавец SoVAni. Соблюдай инструкции и защищай правила."),
            max_tokens=llm_config.get("max_tokens", 512),
            temperature=llm_config.get("temperature", 0.6),
            metadata=metadata
        )
