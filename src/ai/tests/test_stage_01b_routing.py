"""
Stage 01b (speed fix after the first real-model run): per-role reasoning effort and OpenRouter provider routing,
configurable from env vars, plus the labeler and writer passing their role's reasoning to the client.
"""
import json
from dataclasses import replace
from types import SimpleNamespace
import pytest
from pydantic import BaseModel
from eduhub_ai.config import load_settings
from eduhub_ai.features import extract_deterministic
from eduhub_ai.insights.evidence import EvidencePack
from eduhub_ai.insights.writer import write_texts
from eduhub_ai.labeling.labeler import label_account
from eduhub_ai.labeling.schemas import TaxonomyResponse
from eduhub_ai.llm.client import LLMCall
from eduhub_ai.llm.openrouter import OpenRouterClient
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_shared.fixtures import load_snapshot

class Pair(BaseModel):
    name: str
    count: int

class RecordingCompletions:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.requests.append(kwargs)
        message = SimpleNamespace(content='{"name": "a", "count": 1}')
        return SimpleNamespace(model=kwargs["model"], choices=[SimpleNamespace(message=message)], usage=None)

def client_with(settings) -> tuple[OpenRouterClient, RecordingCompletions]:
    completions = RecordingCompletions()
    fake = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return OpenRouterClient(settings, client=fake), completions

def base_settings(**env: str):
    return load_settings({"OPENROUTER_API_KEY": "sk-test", **env})

# ---------- settings ----------
def test_routing_defaults():
    s = load_settings({})
    assert s.label_reasoning == "off"
    assert s.writer_reasoning == "low"
    assert s.provider_sort == "throughput"
    assert s.providers == ()

def test_routing_custom_values():
    s = load_settings({"AI_LABEL_REASONING": "Minimal", "AI_WRITER_REASONING": "high",
                       "AI_PROVIDER_SORT": "latency", "AI_PROVIDERS": " fireworks, deepinfra ,,"})
    assert s.label_reasoning == "minimal"
    assert s.writer_reasoning == "high"
    assert s.provider_sort == "latency"
    assert s.providers == ("fireworks", "deepinfra")
    assert load_settings({"AI_PROVIDER_SORT": "none"}).provider_sort is None
    assert load_settings({"AI_LABEL_REASONING": "default"}).label_reasoning == "default"

@pytest.mark.parametrize("env", [
    {"AI_LABEL_REASONING": "max"},
    {"AI_WRITER_REASONING": "fast"},
    {"AI_PROVIDER_SORT": "cheapest"},
])
def test_routing_invalid_values_raise(env):
    with pytest.raises(ValueError):
        load_settings(env)

# ---------- request body ----------
@pytest.mark.parametrize(("reasoning", "expected"), [
    ("off", {"enabled": False}),
    ("minimal", {"effort": "minimal"}),
    ("low", {"effort": "low"}),
    ("high", {"effort": "high"}),
])
async def test_reasoning_is_sent_per_call(reasoning, expected):
    client, completions = client_with(base_settings())
    await client.complete_json(model="m", system="s", user="u", schema=Pair, reasoning=reasoning)
    assert completions.requests[0]["extra_body"]["reasoning"] == expected

async def test_default_or_missing_reasoning_sends_nothing():
    client, completions = client_with(base_settings())
    await client.complete_json(model="m", system="s", user="u", schema=Pair, reasoning="default")
    await client.complete_json(model="m", system="s", user="u", schema=Pair)
    assert all("reasoning" not in r["extra_body"] for r in completions.requests)

async def test_provider_sort_and_order_keep_require_parameters():
    client, completions = client_with(base_settings(AI_PROVIDERS="fireworks,deepinfra"))
    await client.complete_json(model="m", system="s", user="u", schema=Pair)
    provider = completions.requests[0]["extra_body"]["provider"]
    assert provider["require_parameters"] is True
    assert provider["sort"] == "throughput"
    assert provider["order"] == ["fireworks", "deepinfra"]

async def test_no_sort_and_no_order_when_disabled():
    client, completions = client_with(base_settings(AI_PROVIDER_SORT="none"))
    await client.complete_json(model="m", system="s", user="u", schema=Pair)
    provider = completions.requests[0]["extra_body"]["provider"]
    assert provider == {"require_parameters": True}

async def test_retry_keeps_the_reasoning():
    client = ScriptedLLMClient(['{"name": "a"}', '{"name": "a", "count": 1}'])
    await client.complete_json(model="m", system="s", user="u", schema=Pair, reasoning="off")
    assert [c.reasoning for c in client.calls] == ["off", "off"]

# ---------- roles ----------
def label_responder(call: LLMCall) -> str:
    if call.schema is TaxonomyResponse:
        return json.dumps({"topics": ["ahorro", "inversiones", "tarjetas"]})
    return json.dumps({"labels": []})

async def test_labeler_uses_the_label_reasoning():
    snapshot = load_snapshot()
    features = {p.id: extract_deterministic(p, []) for p in snapshot.posts}
    client = ScriptedLLMClient([label_responder] * 10)
    settings = replace(load_settings({}), label_reasoning="minimal")
    await label_account(snapshot.posts[:5], features, client, settings)
    assert client.calls
    assert {c.reasoning for c in client.calls} == {"minimal"}

async def test_writer_uses_the_writer_reasoning():
    pack = EvidencePack(handle="demo", post_count=0, kpis=[], findings=[], best_slots=[], top_posts=[],
                        bottom_posts=[])
    answer = json.dumps({"insights": [], "recommendations": [], "explanations": [], "summary": "Hola."})
    client = ScriptedLLMClient([answer] * 4)
    await write_texts(pack, client, replace(load_settings({}), writer_reasoning="medium"))
    assert client.calls
    assert {c.reasoning for c in client.calls} == {"medium"}
