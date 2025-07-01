import os
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional
from ..base import LLMProvider, LLMRequest, LLMResponse, ModelType, LLMError

try:
    from circuitbreaker import circuit
except ImportError:
    # Фолбэк — если нет circuitbreaker
    def circuit(*args, **kwargs):
        def decorator(fn):
            return fn
        return decorator

# Метрики — хук DI-ready
metrics_hook = None

MODEL_PRICING = {
    ModelType.CLAUDE_3_OPUS: 0.015 / 1000,
    ModelType.CLAUDE_3_SONNET: 0.003 / 1000,
}

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

logger = logging.getLogger("llm.providers.claude")
logger.setLevel(logging.INFO)

class SecretsFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "api_key"):
            record.api_key = "***"
        return True
logger.addFilter(SecretsFilter())

class ClaudeProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30, max_retries: int = 3, rate_limiter=None, metrics=None):
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self.supported_models = [ModelType.CLAUDE_3_OPUS, ModelType.CLAUDE_3_SONNET]
        self.rate_limiter = rate_limiter
        self.metrics = metrics

    @property
    def models(self):
        return self.supported_models

    def is_available(self) -> bool:
        return bool(self.api_key)

    def calculate_cost(self, usage: Dict[str, int]) -> float:
        model = usage.get("model", ModelType.CLAUDE_3_SONNET)
        total_tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        price_per_1k = MODEL_PRICING.get(model, 0.003)
        return total_tokens * price_per_1k

    def _validate_history(self, history):
        if history is None:
            return
        if not isinstance(history, list) or not all(isinstance(x, dict) and "role" in x and "content" in x for x in history):
            raise ValueError("History must be a list of {role, content} dicts.")
        if len(history) > 40:
            raise ValueError("History too long")

    def _validate_request(self, request: LLMRequest):
        if request.model not in self.supported_models:
            raise ValueError(f"Модель {request.model} не поддерживается Claude.")
        if not request.prompt or not isinstance(request.prompt, str):
            raise ValueError("Prompt пустой или некорректный.")
        if request.max_tokens < 10 or request.max_tokens > 4096:
            raise ValueError("max_tokens вне допустимого диапазона.")
        self._validate_history(request.history)

    @circuit(failure_threshold=3, recovery_timeout=60)
    async def generate(self, request: LLMRequest) -> LLMResponse:
        self._validate_request(request)
        if not self.api_key:
            return LLMResponse(
                content="",
                model=request.model,
                provider="claude",
                usage={},
                latency_ms=0.0,
                cached=False,
                error=LLMError(code="NO_API_KEY", message="No Claude API key provided"),
            )
        if self.rate_limiter:
            await self.rate_limiter.check(request)
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        if request.history:
            messages.extend(request.history)
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": request.model.value,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": messages,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        attempt = 0
        while attempt < self.max_retries:
            try:
                start = asyncio.get_event_loop().time()
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    coro = session.post(ANTHROPIC_API_URL, json=payload, headers=headers)
                    async with asyncio.wait_for(coro, timeout=self.timeout) as resp:
                        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
                        data = await resp.json()
                        if resp.status != 200:
                            # Не логируем payload! Только коды и сообщения
                            logger.warning(f"Claude API error [{resp.status}]: {data.get('error', {}).get('message', str(data))}")
                            if 500 <= resp.status < 600:
                                attempt += 1
                                await asyncio.sleep(2 ** attempt)
                                continue
                            if self.metrics: self.metrics.record_error("claude", request.model, f"HTTP_{resp.status}")
                            return LLMResponse(
                                content="",
                                model=request.model,
                                provider="claude",
                                usage={},
                                latency_ms=float(latency_ms),
                                cached=False,
                                error=LLMError(
                                    code=f"HTTP_{resp.status}",
                                    message=data.get("error", {}).get("message", str(data)),
                                ),
                            )
                        content = data["content"][0]["text"] if "content" in data and data["content"] else ""
                        usage = data.get("usage", {})
                        usage["model"] = request.model
                        if self.metrics: self.metrics.record_success("claude", request.model, usage)
                        return LLMResponse(
                            content=content,
                            model=request.model,
                            provider="claude",
                            usage=usage,
                            latency_ms=float(latency_ms),
                            cached=False,
                            error=None,
                        )
            except Exception as e:
                logger.exception("Claude API Exception (retrying)" if attempt + 1 < self.max_retries else "Claude API fatal error")
                if attempt + 1 >= self.max_retries:
                    if self.metrics: self.metrics.record_error("claude", request.model, "API_ERROR")
                    return LLMResponse(
                        content="",
                        model=request.model,
                        provider="claude",
                        usage={},
                        latency_ms=0.0,
                        cached=False,
                        error=LLMError(code="API_ERROR", message=str(e)),
                    )
                attempt += 1
                await asyncio.sleep(2 ** attempt)

