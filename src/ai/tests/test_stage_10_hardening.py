"""
Stage 10: demo hardening (no hidden SDK retries, usage/cost totals, a wrong key degrades to templates) and the
alternative pattern models used by the bake-off.
"""
import math
from datetime import UTC, datetime
from types import SimpleNamespace
import httpx2
import numpy as np
import openai
import pytest
from pydantic import BaseModel
from eduhub_ai.analyzer import HybridAnalyzer
from eduhub_ai.config import load_settings
from eduhub_ai.llm.client import LLMError
from eduhub_ai.llm.openrouter import OpenRouterClient
from eduhub_ai.patterns.alternatives import BAKEOFF_MODELS, PairwiseLogisticModel, SklearnPatternModel
from eduhub_ai.patterns.evaluation import pairwise_accuracy
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.testing import check_analyzer

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)

class Pair(BaseModel):
    name: str
    count: int

class Completions:
    def __init__(self, items: list) -> None:
        self.items = list(items)
        self.calls = 0

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls += 1
        item = self.items.pop(0) if len(self.items) > 1 else self.items[0]
        if isinstance(item, Exception):
            raise item
        usage = SimpleNamespace(prompt_tokens=100, completion_tokens=20, cost=0.0004)
        message = SimpleNamespace(content=item)
        return SimpleNamespace(model=kwargs["model"], provider="Test", choices=[SimpleNamespace(message=message)],
                               usage=usage)

def client_with(items: list) -> tuple[OpenRouterClient, Completions]:
    completions = Completions(items)
    settings = load_settings({"OPENROUTER_API_KEY": "sk-test"})
    return OpenRouterClient(settings, client=SimpleNamespace(chat=SimpleNamespace(completions=completions))), \
        completions

def auth_error() -> openai.AuthenticationError:
    request = httpx2.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    return openai.AuthenticationError("bad key", response=httpx2.Response(401, request=request), body=None)

# ---------- client hardening ----------
def test_sdk_does_not_retry_on_its_own():
    client = OpenRouterClient(load_settings({"OPENROUTER_API_KEY": "sk-test"}))
    assert client._client.max_retries == 0

async def test_usage_totals_accumulate_tokens_cost_and_failures():
    client, _ = client_with(['{"name": "a", "count": 1}', '{"name": "b", "count": 2}', auth_error()])
    await client.complete_json(model="m", system="s", user="u", schema=Pair)
    await client.complete_json(model="m", system="s", user="u", schema=Pair)
    with pytest.raises(LLMError):
        await client.complete_json(model="m", system="s", user="u", schema=Pair)
    usage = client.usage
    assert usage.calls == 2
    assert usage.failures == 1
    assert usage.prompt_tokens == 200
    assert usage.completion_tokens == 40
    assert usage.cost == pytest.approx(0.0008)

async def test_usage_requests_cost_accounting_from_openrouter():
    client, completions = client_with(['{"name": "a", "count": 1}'])
    requests = []
    original = completions.create

    async def recording(**kwargs: object) -> SimpleNamespace:
        requests.append(kwargs)
        return await original(**kwargs)

    completions.create = recording
    await client.complete_json(model="m", system="s", user="u", schema=Pair)
    assert requests[0]["extra_body"]["usage"] == {"include": True}

async def test_wrong_api_key_degrades_to_a_template_report():
    client, completions = client_with([auth_error()])
    settings = load_settings({"OPENROUTER_API_KEY": "sk-wrong"})
    report = await check_analyzer(HybridAnalyzer(settings, client, clock=lambda: NOW), load_snapshot())
    assert report.insights
    assert report.summary.startswith("Analizamos 40 posts de @")
    assert completions.calls >= 1
    assert client.usage.calls == 0

# ---------- bake-off models ----------
def photo_data(n: int = 150, seed: int = 0):
    rng = np.random.default_rng(seed)
    rows, scores = [], []
    for _ in range(n):
        photo = rng.random() < 0.4
        rows.append({"media_type": "photo" if photo else "text", "topic": str(rng.choice(["a", "b", "c"]))})
        scores.append(math.exp((math.log(2.0) if photo else 0.0) + rng.normal(0, 0.3)))
    return rows, scores

def test_bakeoff_has_the_planned_models():
    assert set(BAKEOFF_MODELS) == {"ridge", "elasticnet", "bayesian_ridge", "huber", "pairwise_logistic",
                                   "hist_gb"}

@pytest.mark.parametrize("name", sorted(BAKEOFF_MODELS))
def test_every_bakeoff_model_ranks_better_than_chance_on_a_real_effect(name):
    accuracy = pairwise_accuracy(BAKEOFF_MODELS[name], *photo_data())
    assert accuracy > 0.65, name

def test_alternative_models_predict_positive_scores_and_handle_unknown_levels():
    rows, scores = photo_data()
    for model in (SklearnPatternModel.elasticnet(), PairwiseLogisticModel()):
        model.fit(rows, scores)
        assert model.predict({"media_type": "photo", "topic": "a"}) > model.predict({"media_type": "text",
                                                                                     "topic": "a"})
        assert model.predict({"media_type": "nunca", "topic": "zzz"}) > 0
        assert model.effects() == []
