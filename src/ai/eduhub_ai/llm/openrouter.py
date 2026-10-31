"""
OpenRouterClient: the real LLMClient, using the OpenAI-compatible SDK against OpenRouter.
"""
import asyncio
import copy
import logging
import time
from dataclasses import dataclass
from typing import Any
import openai
from pydantic import BaseModel
from eduhub_ai.config import AISettings
from eduhub_ai.llm.client import LLMCall, LLMError, complete_with_retry
from eduhub_shared.errors import RateLimitedError

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
SDK_MAX_RETRIES = 0
RATE_LIMITED_MESSAGE = "Estamos recibiendo muchas consultas a la IA. Probá de nuevo en un minuto."
logger = logging.getLogger(__name__)

@dataclass
class Usage:
    """
    Running totals for one client: successful calls, failed calls, tokens and cost in USD (as OpenRouter reports
    it; 0 when it doesn't).
    """
    calls: int = 0
    failures: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0

class OpenRouterClient:
    """
    Structured-output calls via OpenRouter, with fallback models, a per-call timeout and a concurrency limit.
    The SDK never retries on its own (a timed-out call would otherwise double the wait); our callers decide.
    """
    def __init__(self, settings: AISettings, client: Any = None) -> None:
        """
        Use the injected AsyncOpenAI-like client, or build one from settings (requires OPENROUTER_API_KEY).
        """
        if client is None:
            if not settings.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY is not set")
            client = openai.AsyncOpenAI(
                api_key=settings.openrouter_api_key, base_url=OPENROUTER_BASE_URL, max_retries=SDK_MAX_RETRIES
            )
        self.settings = settings
        self.usage = Usage()
        self._client = client
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)

    async def complete_json[T: BaseModel](
        self, *, model: str, system: str, user: str, schema: type[T], temperature: float | None = None,
        reasoning: str | None = None,
    ) -> T:
        """
        Send the prompt and return the response validated as schema (one retry on invalid output).
        """
        return await complete_with_retry(LLMCall(model, system, user, schema, temperature, reasoning), self._send)

    async def _send(self, call: LLMCall) -> str | None:
        """
        Make one chat completion request and return the message content, mapping provider errors.
        """
        request = self._build_request(call)
        async with self._semaphore:
            started = time.perf_counter()
            try:
                response = await self._request(request)
            except openai.RateLimitError as error:
                raise RateLimitedError(RATE_LIMITED_MESSAGE) from error
            except openai.APIConnectionError as error:
                raise LLMError(f"OpenRouter connection failed: {error}", retryable=True) from error
            except openai.APIStatusError as error:
                retryable = error.status_code >= 500
                raise LLMError(f"OpenRouter returned {error.status_code}: {error}", retryable=retryable) from error
            except openai.OpenAIError as error:
                raise LLMError(f"OpenRouter call failed: {error}") from error
        self._record(call, response, time.perf_counter() - started)
        if not response.choices:
            return None
        return response.choices[0].message.content

    async def _request(self, request: dict[str, Any]) -> Any:
        """
        Send one request, counting it as a failure if it raises.
        """
        try:
            return await self._client.chat.completions.create(**request)
        except Exception:
            self.usage.failures += 1
            raise

    def _build_request(self, call: LLMCall) -> dict[str, Any]:
        """
        Build the keyword arguments for chat.completions.create.
        """
        extra_body: dict[str, Any] = {"provider": self._provider_preferences(), "usage": {"include": True}}
        reasoning = reasoning_body(call.reasoning)
        if reasoning is not None:
            extra_body["reasoning"] = reasoning
        if self.settings.fallback_models:
            extra_body["models"] = [call.model, *self.settings.fallback_models]
        request: dict[str, Any] = {
            "model": call.model,
            "messages": [{"role": "system", "content": call.system}, {"role": "user", "content": call.user}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": call.schema.__name__, "strict": True, "schema": strict_schema(call.schema)},
            },
            "extra_body": extra_body,
            "timeout": self.settings.llm_timeout_s,
        }
        if call.temperature is not None:
            request["temperature"] = call.temperature
        return request

    def _provider_preferences(self) -> dict[str, Any]:
        """
        OpenRouter provider routing: only endpoints that support our parameters (strict json_schema), sorted
        by AI_PROVIDER_SORT and, if set, tried in the AI_PROVIDERS order first.
        """
        provider: dict[str, Any] = {"require_parameters": True}
        if self.settings.provider_sort:
            provider["sort"] = self.settings.provider_sort
        if self.settings.providers:
            provider["order"] = list(self.settings.providers)
        return provider

    def _record(self, call: LLMCall, response: Any, latency_s: float) -> None:
        """
        Add the call to the usage totals and log the model and provider that answered (OpenRouter adds
        "provider" to the response), token usage, cost and latency.
        """
        usage = getattr(response, "usage", None)
        self.usage.calls += 1
        self.usage.prompt_tokens += getattr(usage, "prompt_tokens", None) or 0
        self.usage.completion_tokens += getattr(usage, "completion_tokens", None) or 0
        self.usage.cost += float(getattr(usage, "cost", None) or 0.0)
        logger.info(
            "llm call schema=%s requested=%s answered=%s provider=%s reasoning=%s prompt_tokens=%s "
            "completion_tokens=%s latency=%.2fs",
            call.schema.__name__, call.model, getattr(response, "model", None), getattr(response, "provider", None),
            call.reasoning,
            getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None), latency_s,
        )

def reasoning_body(level: str | None) -> dict[str, Any] | None:
    """
    OpenRouter's reasoning parameter for an effort level: "off" disables thinking, None/"default" sends nothing.
    """
    if level is None or level == "default":
        return None
    if level == "off":
        return {"enabled": False}
    return {"effort": level}

def strict_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """
    The model's JSON schema with additionalProperties=false on every object, as strict mode requires.
    """
    result = copy.deepcopy(schema.model_json_schema())
    _forbid_extra(result)
    return result

def _forbid_extra(node: Any) -> None:
    """
    Recursively set additionalProperties=false on every object schema inside node.
    """
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            node.setdefault("additionalProperties", False)
        for value in node.values():
            _forbid_extra(value)
    elif isinstance(node, list):
        for value in node:
            _forbid_extra(value)
