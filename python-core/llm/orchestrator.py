import hashlib, json, time, asyncio, logging, yaml
from typing import List, Dict, Optional, Any
from .base import LLMProvider, LLMRequest, LLMResponse
from .cache import SecureCacheManager
from .metrics import MetricsProvider
from .rate_limiter import TokenBucketRateLimiter, RateLimitExceeded

def _safe_hash(data: dict) -> str:
    # Санитайзим и ограничиваем поля
    d = {
        "tenant": str(data.get("tenant", ""))[:32],
        "model": str(data.get("model", ""))[:32],
        "prompt": str(data.get("prompt", ""))[:512],
        "system_prompt": str(data.get("system_prompt", ""))[:256],
        "params": f'{data.get("temperature", "0.7")}:{data.get("max_tokens", "1000")}',
    }
    serialized = json.dumps(d, sort_keys=True, separators=(',', ':'))
    base_hash = hashlib.sha256(serialized.encode()).digest()
    return "llm:v2:" + hashlib.blake2s(base_hash, digest_size=16).hexdigest()

class ProviderState:
    def __init__(self, threshold=5, recovery_timeout=60):
        self.failures = 0
        self.last_failure = 0
        self.state = "closed"
        self.threshold = threshold
        self.recovery_timeout = recovery_timeout

    def should_try(self) -> bool:
        if self.state == "open" and (time.time() - self.last_failure < self.recovery_timeout):
            return False
        if self.state == "open" and (time.time() - self.last_failure >= self.recovery_timeout):
            self.state = "half-open"
        return True

    def register_failure(self):
        self.failures += 1
        self.last_failure = time.time()
        if self.failures >= self.threshold:
            self.state = "open"

    def register_success(self):
        self.failures = 0
        self.state = "closed"

class AdaptiveFallbackChain:
    def __init__(self, config_path: str):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        self.weights = self.config.get("fallback_chain", {})
        self.chain = self._build_chain()

    def _build_chain(self):
        return [p for p, w in sorted(self.weights.items(), key=lambda x: -x[1])]

    def update(self, provider: str, success: bool):
        # адаптация веса по успешности (примерно)
        if provider in self.weights:
            if success:
                self.weights[provider] = min(1.0, self.weights[provider] + 0.05)
            else:
                self.weights[provider] = max(0.01, self.weights[provider] - 0.15)
        self.chain = self._build_chain()

class LLMOrchestrator:
    def __init__(
        self,
        providers: Dict[str, LLMProvider],
        cache: Optional[SecureCacheManager] = None,
        limiter: Optional[TokenBucketRateLimiter] = None,
        metrics: Optional[MetricsProvider] = None,
        fallback_chain: Optional[AdaptiveFallbackChain] = None,
        circuit_breaker_conf: Optional[dict] = None
    ):
        self.providers = providers
        self.cache = cache
        self.limiter = limiter
        self.metrics = metrics
        self.fallback_chain = fallback_chain or AdaptiveFallbackChain("config/orchestrator.yaml")
        self.provider_states = {k: ProviderState(**(circuit_breaker_conf or {})) for k in providers}

    async def generate(self, request: LLMRequest, tenant_id: str, user_id: str, cache_ttl=None) -> LLMResponse:
        cache_key = _safe_hash({
            "tenant": tenant_id,
            "model": request.model,
            "prompt": request.prompt,
            "system_prompt": request.system_prompt,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        })

        # Rate limiting
        if self.limiter:
            try:
                await self.limiter.check(tenant_id, user_id, str(request.model))
            except RateLimitExceeded as e:
                return LLMResponse(content="", model=request.model, provider="rate_limiter", usage={}, latency_ms=0.0, cached=False, error={"code": "RATE_LIMIT", "message": str(e)})

        # Cache
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                if self.metrics:
                    await self.metrics.record_success(tenant_id, "cache", str(request.model), cached.get("usage", {}), 0.0, 0.0)
                return LLMResponse(**cached, cached=True)

        # Параллельная обработка fallback (на первых двух провайдерах для ускорения, остальное — по цепочке)
        chain = self.fallback_chain.chain
        provider_states = self.provider_states
        results = {}
        tasks = {}
        for provider_name in chain:
            if not provider_states[provider_name].should_try():
                continue
            provider = self.providers[provider_name]
            # Легковесная конкурентная обработка (только для топовых провайдеров)
            tasks[provider_name] = asyncio.create_task(provider.generate(request))

        done, pending = await asyncio.wait(list(tasks.values()), return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        for provider_name, task in tasks.items():
            if task in done:
                try:
                    resp = task.result()
                    provider_states[provider_name].register_success()
                    self.fallback_chain.update(provider_name, True)
                    if self.metrics:
                        await self.metrics.record_success(tenant_id, provider_name, str(request.model), resp.usage, getattr(resp, "cost", 0.0), getattr(resp, "latency_ms", 0.0))
                    if self.cache and not resp.cached:
                        await self.cache.set(cache_key, resp.__dict__, ttl=cache_ttl)
                    resp.cached = False
                    resp.provider = provider_name
                    return resp
                except Exception as e:
                    provider_states[provider_name].register_failure()
                    self.fallback_chain.update(provider_name, False)
                    if self.metrics:
                        await self.metrics.record_error(tenant_id, provider_name, str(request.model), type(e).__name__)
        # Если все провайдеры упали
        return LLMResponse(content="", model=request.model, provider="none", usage={}, latency_ms=0.0, cached=False, error={"code": "FALLBACK_FAILED", "message": "All providers failed"})

    async def health_check(self):
        results = {}
        for name, provider in self.providers.items():
            try:
                start = time.monotonic()
                await provider.generate(LLMRequest(prompt="ping", model="gpt-4-turbo"))
                results[name] = {"status": "healthy", "latency": time.monotonic() - start}
            except Exception as e:
                results[name] = {"status": "unhealthy", "error": str(e)}
        return results

