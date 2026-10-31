"""
OpenRouterClient: the real LLMClient, using the OpenAI-compatible SDK against OpenRouter.
"""
import asyncio
import copy
import logging
import time
from typing import Any
import openai
from pydantic import BaseModel
from eduhub_ai.config import AISettings
from eduhub_ai.llm.client import LLMCall, LLMError, complete_with_retry
from eduhub_shared.errors import RateLimitedError

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
RATE_LIMITED_MESSAGE = "Estamos recibiendo muchas consultas a la IA. Probá de nuevo en un minuto."
logger = logging.getLogger(__name__)

class OpenRouterClient:
    """
    Structured-output calls via OpenRouter, with fallback models, a per-call timeout and a concurrency limit.
    """
    def __init__(self, settings: AISettings, client: Any = None) -> None:
        """
        Use the injected AsyncOpenAI-like client, or build one from settings (requires OPENROUTER_API_KEY).
        """
        if client is None:
            if not settings.openrouter_api_key:
                raise ValueError("OPENROUTER_API_KEY is not set")
            client = openai.AsyncOpenAI(
                api_key=settings.openrouter_api_key, base_url=OPENROUTER_BASE_URL, max_retries=1
            )
        self.settings = settings
        self._client = client
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)

    async def complete_json[T: BaseModel](
        self, *, model: str, system: str, user: str, schema: type[T], temperature: float | None = None
    ) -> T:
        """
        Send the prompt and return the response validated as schema (one retry on invalid output).
        """
        return await complete_with_retry(LLMCall(model, system, user, schema, temperature), self._send)

    async def _send(self, call: LLMCall) -> str | None:
        """
        Make one chat completion request and return the message content, mapping provider errors.
        """
        request = self._build_request(call)
        async with self._semaphore:
            started = time.perf_counter()
            try:
                response = await self._client.chat.completions.create(**request)
            except openai.RateLimitError as error:
                raise RateLimitedError(RATE_LIMITED_MESSAGE) from error
            except openai.APIConnectionError as error:
                raise LLMError(f"OpenRouter connection failed: {error}", retryable=True) from error
            except openai.APIStatusError as error:
                retryable = error.status_code >= 500
                raise LLMError(f"OpenRouter returned {error.status_code}: {error}", retryable=retryable) from error
            except openai.OpenAIError as error:
                raise LLMError(f"OpenRouter call failed: {error}") from error
        self._log(call, response, time.perf_counter() - started)
        if not response.choices:
            return None
        return response.choices[0].message.content

    def _build_request(self, call: LLMCall) -> dict[str, Any]:
        """
        Build the keyword arguments for chat.completions.create.
        """
        extra_body: dict[str, Any] = {"provider": {"require_parameters": True}}
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

    def _log(self, call: LLMCall, response: Any, latency_s: float) -> None:
        """
        Log the model that answered, token usage and latency.
        """
        usage = getattr(response, "usage", None)
        logger.info(
            "llm call schema=%s requested=%s answered=%s prompt_tokens=%s completion_tokens=%s latency=%.2fs",
            call.schema.__name__, call.model, getattr(response, "model", None),
            getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None), latency_s,
        )

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
