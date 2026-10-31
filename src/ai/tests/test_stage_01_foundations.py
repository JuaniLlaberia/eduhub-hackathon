"""
Stage 01: settings (AISettings / load_settings) and the LLM layer (LLMClient, ScriptedLLMClient, OpenRouterClient).
No network: OpenRouterClient gets a fake AsyncOpenAI-like object.
"""
import asyncio
from dataclasses import replace
from types import SimpleNamespace
import httpx2
import openai
import pytest
from pydantic import BaseModel
from eduhub_ai.config import AISettings, load_settings
from eduhub_ai.llm.client import LLMError, parse_or_raise
from eduhub_ai.llm.openrouter import OpenRouterClient
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_shared.errors import RateLimitedError

class Pair(BaseModel):
    name: str
    count: int

class FakeCompletions:
    def __init__(self, contents: list[str | Exception], delay_s: float = 0.0) -> None:
        self.contents = list(contents)
        self.delay_s = delay_s
        self.requests: list[dict] = []
        self.in_flight = 0
        self.peak = 0

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.requests.append(kwargs)
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            await asyncio.sleep(self.delay_s)
            item = self.contents.pop(0) if len(self.contents) > 1 else self.contents[0]
            if isinstance(item, Exception):
                raise item
            message = SimpleNamespace(content=item)
            usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)
            return SimpleNamespace(model=kwargs["model"], choices=[SimpleNamespace(message=message)], usage=usage)
        finally:
            self.in_flight -= 1

def fake_openai(completions: FakeCompletions) -> SimpleNamespace:
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))

def settings(**overrides: object) -> AISettings:
    return replace(load_settings({"OPENROUTER_API_KEY": "sk-test"}), **overrides)

def openai_request() -> httpx2.Request:
    return httpx2.Request("POST", "https://openrouter.ai/api/v1/chat/completions")

# ---------- settings ----------
def test_load_settings_defaults():
    s = load_settings({})
    assert s.openrouter_api_key is None
    assert s.label_model == "deepseek/deepseek-v4.1-flash"
    assert s.writer_model == "deepseek/deepseek-v4.1-flash"
    assert s.fallback_models == ()
    assert s.llm_timeout_s == 30
    assert s.max_concurrency == 8
    assert s.enable_llm is True

def test_load_settings_custom_values():
    s = load_settings({
        "OPENROUTER_API_KEY": "sk-abc",
        "AI_LABEL_MODEL": "a/label",
        "AI_WRITER_MODEL": "b/writer",
        "AI_FALLBACK_MODELS": " x/one, y/two ,,",
        "AI_LLM_TIMEOUT_S": "12.5",
        "AI_MAX_CONCURRENCY": "3",
        "AI_ENABLE_LLM": "0",
    })
    assert s.openrouter_api_key == "sk-abc"
    assert s.label_model == "a/label"
    assert s.writer_model == "b/writer"
    assert s.fallback_models == ("x/one", "y/two")
    assert s.llm_timeout_s == 12.5
    assert s.max_concurrency == 3
    assert s.enable_llm is False

def test_load_settings_empty_key_is_none_and_enable_llm_one_is_true():
    s = load_settings({"OPENROUTER_API_KEY": "", "AI_ENABLE_LLM": "1"})
    assert s.openrouter_api_key is None
    assert s.enable_llm is True

@pytest.mark.parametrize("env", [
    {"AI_MAX_CONCURRENCY": "lots"},
    {"AI_MAX_CONCURRENCY": "0"},
    {"AI_LLM_TIMEOUT_S": "soon"},
    {"AI_ENABLE_LLM": "maybe"},
])
def test_load_settings_invalid_values_raise_value_error(env):
    with pytest.raises(ValueError):
        load_settings(env)

def test_settings_are_frozen():
    s = load_settings({})
    with pytest.raises(AttributeError):
        s.max_concurrency = 1

def test_load_settings_reads_os_environ_by_default(monkeypatch):
    monkeypatch.setenv("AI_MAX_CONCURRENCY", "5")
    assert load_settings().max_concurrency == 5

# ---------- shared parsing helper ----------
def test_parse_or_raise_returns_validated_object():
    assert parse_or_raise('{"name": "a", "count": 2}', Pair) == Pair(name="a", count=2)

@pytest.mark.parametrize("text", ["not json", '{"name": "a"}', None])
def test_parse_or_raise_invalid_raises_retryable_llm_error(text):
    with pytest.raises(LLMError) as info:
        parse_or_raise(text, Pair)
    assert info.value.retryable is True

# ---------- ScriptedLLMClient ----------
async def test_scripted_returns_validated_object_and_records_call():
    client = ScriptedLLMClient(['{"name": "hola", "count": 3}'])
    result = await client.complete_json(model="m", system="sys", user="usr", schema=Pair, temperature=0.2)
    assert result == Pair(name="hola", count=3)
    assert len(client.calls) == 1
    call = client.calls[0]
    assert (call.model, call.system, call.user, call.schema, call.temperature) == ("m", "sys", "usr", Pair, 0.2)

async def test_scripted_callable_response_receives_the_call():
    client = ScriptedLLMClient([lambda call: f'{{"name": "{call.model}", "count": 1}}'])
    result = await client.complete_json(model="echo", system="s", user="u", schema=Pair)
    assert result == Pair(name="echo", count=1)

async def test_invalid_then_valid_retries_once_with_validation_error_in_user_message():
    client = ScriptedLLMClient(['{"name": "a"}', '{"name": "a", "count": 1}'])
    result = await client.complete_json(model="m", system="s", user="original prompt", schema=Pair)
    assert result == Pair(name="a", count=1)
    assert len(client.calls) == 2
    retry = client.calls[1]
    assert retry.user.startswith("original prompt")
    assert "count" in retry.user[len("original prompt"):]
    assert retry.model == "m"
    assert retry.system == "s"

async def test_invalid_twice_raises_llm_error():
    client = ScriptedLLMClient(["not json", '{"count": "x"}'])
    with pytest.raises(LLMError):
        await client.complete_json(model="m", system="s", user="u", schema=Pair)
    assert len(client.calls) == 2

async def test_queued_rate_limited_error_propagates_unchanged_without_retry():
    error = RateLimitedError("Estamos recibiendo muchas consultas. Probá de nuevo en un minuto.")
    client = ScriptedLLMClient([error, '{"name": "a", "count": 1}'])
    with pytest.raises(RateLimitedError) as info:
        await client.complete_json(model="m", system="s", user="u", schema=Pair)
    assert info.value is error
    assert len(client.calls) == 1

async def test_scripted_without_responses_left_raises_llm_error():
    client = ScriptedLLMClient([])
    with pytest.raises(LLMError):
        await client.complete_json(model="m", system="s", user="u", schema=Pair)

# ---------- OpenRouterClient ----------
async def test_openrouter_builds_request_with_strict_schema_and_fallbacks():
    completions = FakeCompletions(['{"name": "a", "count": 1}'])
    client = OpenRouterClient(settings(fallback_models=("fb/one", "fb/two"), llm_timeout_s=7.0),
                              client=fake_openai(completions))
    result = await client.complete_json(model="main/model", system="sys", user="usr", schema=Pair, temperature=0.3)
    assert result == Pair(name="a", count=1)
    request = completions.requests[0]
    assert request["model"] == "main/model"
    assert request["messages"] == [{"role": "system", "content": "sys"}, {"role": "user", "content": "usr"}]
    assert request["temperature"] == 0.3
    assert request["timeout"] == 7.0
    response_format = request["response_format"]
    assert response_format["type"] == "json_schema"
    json_schema = response_format["json_schema"]
    assert json_schema["name"] == "Pair"
    assert json_schema["strict"] is True
    assert set(json_schema["schema"]["properties"]) == {"name", "count"}
    assert json_schema["schema"]["additionalProperties"] is False
    assert request["extra_body"]["provider"]["require_parameters"] is True
    assert request["extra_body"]["models"] == ["main/model", "fb/one", "fb/two"]

async def test_openrouter_without_fallbacks_sends_no_models_list():
    completions = FakeCompletions(['{"name": "a", "count": 1}'])
    client = OpenRouterClient(settings(), client=fake_openai(completions))
    await client.complete_json(model="main/model", system="s", user="u", schema=Pair)
    extra_body = completions.requests[0]["extra_body"]
    assert extra_body["provider"]["require_parameters"] is True
    assert "models" not in extra_body

async def test_openrouter_retries_once_on_invalid_output():
    completions = FakeCompletions(['{"name": "a"}', '{"name": "a", "count": 4}'])
    client = OpenRouterClient(settings(), client=fake_openai(completions))
    result = await client.complete_json(model="m", system="s", user="original", schema=Pair)
    assert result == Pair(name="a", count=4)
    assert len(completions.requests) == 2
    retry_user = completions.requests[1]["messages"][-1]["content"]
    assert retry_user.startswith("original")
    assert "count" in retry_user[len("original"):]

async def test_openrouter_maps_429_to_rate_limited_error():
    response = httpx2.Response(429, request=openai_request())
    completions = FakeCompletions([openai.RateLimitError("rate limited", response=response, body=None)])
    client = OpenRouterClient(settings(), client=fake_openai(completions))
    with pytest.raises(RateLimitedError):
        await client.complete_json(model="m", system="s", user="u", schema=Pair)

@pytest.mark.parametrize("error", [
    openai.APITimeoutError(request=openai_request()),
    openai.APIConnectionError(request=openai_request()),
    openai.APIStatusError("boom", response=httpx2.Response(502, request=openai_request()), body=None),
])
async def test_openrouter_maps_other_failures_to_llm_error(error):
    completions = FakeCompletions([error])
    client = OpenRouterClient(settings(), client=fake_openai(completions))
    with pytest.raises(LLMError):
        await client.complete_json(model="m", system="s", user="u", schema=Pair)

def test_openrouter_without_key_and_without_injected_client_raises():
    with pytest.raises(ValueError):
        OpenRouterClient(load_settings({}))

async def test_openrouter_respects_max_concurrency():
    completions = FakeCompletions(['{"name": "a", "count": 1}'], delay_s=0.02)
    client = OpenRouterClient(settings(max_concurrency=2), client=fake_openai(completions))
    results = await asyncio.gather(*[
        client.complete_json(model="m", system="s", user=f"u{i}", schema=Pair) for i in range(6)
    ])
    assert len(results) == 6
    assert completions.peak == 2
