import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional
from ..base import LLMProvider, LLMRequest, LLMResponse, ModelType, LLMError

# Тарифы
MODEL_PRICING = {
    ModelType.GPT_4_TURBO: 0.01 / 1000,
    ModelType.GPT_4: 0.03 / 1000,
    ModelType.GPT_35_TURBO: 0.001 / 1000,
}

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

logger = logging.getLogger("llm.providers.openai")
logger.setLevel(logging.INFO)

class SecretsFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "api_key"):
            record.api_key = "***"
        return True

logger.addFilter(SecretsFilter())

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, timeout: int = 30, max_retries: int = 3, rate_limiter=None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self.supported_models = [ModelType.GPT_4_TURBO, ModelType.GPT_4, ModelType.GPT_35_TURBO]
        self.rate_limiter = rate_limiter  # DI-ready

    @property
    def models(self):
        return self.supported_models

    def is_available(self) -> bool:
        return bool(self.api_key)

    def calculate_cost(self, usage: Dict[str, int]) -> float:
        model = usage.get("model", ModelType.GPT_4_TURBO)
        total_tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        price_per_1k = MODEL_PRICING.get(model, 0.01)
        return total_tokens * price_per_1k

    def _validate_request(self, request: LLMRequest):
        if request.model not in self.supported_models:
            raise ValueError(f"Модель {request.model} не поддерживается этим провайдером.")
        if not request.prompt or not isinstance(request.prompt, str):
            raise ValueError("Prompt пустой или некорректный.")
        if request.max_tokens < 10 or request.max_tokens > 4096:
            raise ValueError("max_tokens вне допустимого диапазона.")

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self._validate_request(request)
        if not self.api_key:
            return LLMResponse(
                content="",
                model=request.model,
                provider="openai",
                usage={},
                latency_ms=0.0,
                cached=False,
                error=LLMError(code="NO_API_KEY", message="No OpenAI API key provided"),
            )
        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.check(request)
        payload = {
            "model": request.model.value,
            "messages": [],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        if request.system_prompt:
            payload["messages"].append({"role": "system", "content": request.system_prompt})
        if request.history:
            payload["messages"].extend(request.history)
        payload["messages"].append({"role": "user", "content": request.prompt})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        attempt = 0
        while attempt < self.max_retries:
            try:
                start = asyncio.get_event_loop().time()
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(OPENAI_API_URL, json=payload, headers=headers) as resp:
                        latency_ms = (asyncio.get_event_loop().time() - start) * 1000
                        data = await resp.json()
                        if resp.status != 200:
                            logger.warning(f"OpenAI API error [{resp.status}]: {data}")
                            # Retry only on server-side errors
                            if 500 <= resp.status < 600:
                                attempt += 1
                                await asyncio.sleep(2 ** attempt)
                                continue
                            return LLMResponse(
                                content="",
                                model=request.model,
                                provider="openai",
                                usage={},
                                latency_ms=float(latency_ms),
                                cached=False,
                                error=LLMError(
                                    code=f"HTTP_{resp.status}",
                                    message=data.get("error", {}).get("message", str(data)),
                                ),
                            )
                        content = data["choices"][0]["message"]["content"]
                        usage = data.get("usage", {})
                        usage["model"] = request.model
                        # Хук на метрику
                        # if metrics: metrics.record_success(...)
                        return LLMResponse(
                            content=content,
                            model=request.model,
                            provider="openai",
                            usage=usage,
                            latency_ms=float(latency_ms),
                            cached=False,
                            error=None,
                        )
            except Exception as e:
                logger.exception("OpenAI API Exception (retrying)" if attempt + 1 < self.max_retries else "OpenAI API fatal error")
                if attempt + 1 >= self.max_retries:
                    return LLMResponse(
                        content="",
                        model=request.model,
                        provider="openai",
                        usage={},
                        latency_ms=0.0,
                        cached=False,
                        error=LLMError(code="API_ERROR", message=str(e)),
                    )
                attempt += 1
                await asyncio.sleep(2 ** attempt)

