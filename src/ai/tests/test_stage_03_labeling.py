"""
Stage 03: semantic labeling (per-account taxonomy + batch labels for topic, tone, sentiment, hook, CTA).
All LLM calls go through ScriptedLLMClient. The responder below reads post ids from the batch prompt, where each
post is serialized as JSON with an "id" key, so tests don't depend on batch scheduling order.
"""
import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import pytest
from pydantic import ValidationError
from eduhub_ai.config import load_settings
from eduhub_ai.features.deterministic import extract_deterministic
from eduhub_ai.labeling import prompts
from eduhub_ai.labeling.labeler import (
    apply_labels,
    build_taxonomy,
    label_account,
    label_posts,
    sample_for_taxonomy,
)
from eduhub_ai.labeling.schemas import (
    CTA_LABELS,
    HOOK_LABELS,
    TONE_LABELS,
    PostLabel,
    TaxonomyResponse,
    label_batch_schema,
)
from eduhub_ai.llm.client import LLMCall, LLMError
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_shared.errors import RateLimitedError
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.models import Post, PostMetrics

NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
SETTINGS = load_settings({})
TAXONOMY = ["Ahorro", "inversiones", "impuestos", "cripto", "humor"]
SEMANTIC = {"topic", "tone", "sentiment", "hook", "cta"}
IDS_IN_PROMPT = re.compile(r'"id": "([^"]+)"')

def make_post(i: int, text: str | None = None, hashtags: list[str] | None = None) -> Post:
    return Post(
        id=f"p{i}",
        author_handle="demo",
        text=text or f"Post número {i} sobre plata",
        created_at=NOW - timedelta(days=3, hours=i),
        url=f"https://x.com/demo/status/{i}",
        hashtags=hashtags or [],
        metrics=PostMetrics(impressions=1000, likes=10, reposts=0, quotes=0, replies=0, bookmarks=0),
    )

def make_posts(n: int) -> list[Post]:
    return [make_post(i) for i in range(n)]

def features_of(posts: list[Post]) -> dict:
    return {p.id: extract_deterministic(p, []) for p in posts}

def label_json(post_id: str, topic: str = "ahorro", sentiment: float = 0.5) -> dict:
    return {"post_id": post_id, "topic": topic, "tone": "informativo", "sentiment": sentiment,
            "hook": "pregunta", "cta": "guardar"}

class Responder:
    """
    Fake LLM: answers the taxonomy call with a fixed list and each label batch with labels for the ids it sees.
    """
    def __init__(self, taxonomy: list[str] | None = None, topic: str = "ahorro", fail_ids: set[str] | None = None,
                 drop_once: set[str] | None = None, extra_ids: list[str] | None = None,
                 fail_taxonomy: bool = False) -> None:
        self.taxonomy = TAXONOMY if taxonomy is None else taxonomy
        self.topic = topic
        self.fail_ids = fail_ids or set()
        self.drop_once = set(drop_once or set())
        self.extra_ids = extra_ids or []
        self.fail_taxonomy = fail_taxonomy
        self.taxonomy_calls: list[LLMCall] = []
        self.label_calls: list[list[str]] = []

    def __call__(self, call: LLMCall) -> str:
        if call.schema is TaxonomyResponse:
            self.taxonomy_calls.append(call)
            if self.fail_taxonomy:
                raise LLMError("taxonomy down", retryable=True)
            return json.dumps({"topics": self.taxonomy})
        ids = IDS_IN_PROMPT.findall(call.user)
        self.label_calls.append(ids)
        if self.fail_ids & set(ids):
            raise LLMError("batch down", retryable=True)
        answered = [i for i in ids if i not in self.drop_once]
        self.drop_once -= set(ids)
        labels = [label_json(i, self.topic) for i in [*answered, *self.extra_ids]]
        return json.dumps({"labels": labels})

def scripted(responder: Responder, n: int = 50) -> ScriptedLLMClient:
    return ScriptedLLMClient([responder] * n)

# ---------- label sets and schemas ----------
def test_label_sets_match_the_plan():
    assert set(TONE_LABELS) == {"informativo", "opinión", "humor", "personal", "conversacional", "promoción",
                                "inspiracional"}
    assert set(HOOK_LABELS) == {"pregunta", "dato", "afirmación fuerte", "historia", "lista", "ninguno"}
    assert set(CTA_LABELS) == {"guardar", "responder", "compartir", "seguir", "link", "ninguno"}

def test_post_label_rejects_sentiment_out_of_range():
    with pytest.raises(ValidationError):
        PostLabel.model_validate(label_json("p1", sentiment=1.5))
    with pytest.raises(ValidationError):
        PostLabel.model_validate(label_json("p1", sentiment=-1.01))
    assert PostLabel.model_validate(label_json("p1", sentiment=-1.0)).sentiment == -1.0

def test_post_label_rejects_unknown_tone():
    bad = label_json("p1") | {"tone": "furioso"}
    with pytest.raises(ValidationError):
        PostLabel.model_validate(bad)

def test_batch_schema_restricts_topics_to_the_taxonomy():
    schema = label_batch_schema(["ahorro", "cripto", "otros"])
    assert schema.model_validate({"labels": [label_json("p1", "cripto")]}).labels[0].topic == "cripto"
    with pytest.raises(ValidationError):
        schema.model_validate({"labels": [label_json("p1", "fútbol")]})
    enum_values = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    assert '"ahorro"' in enum_values and '"otros"' in enum_values

async def test_invalid_topic_goes_through_the_retry_path():
    posts = make_posts(2)
    bad = json.dumps({"labels": [label_json("p0", "fútbol"), label_json("p1", "fútbol")]})
    good = json.dumps({"labels": [label_json("p0"), label_json("p1")]})
    client = ScriptedLLMClient([bad, good])
    labels = await label_posts(posts, ["ahorro", "otros"], client, SETTINGS)
    assert set(labels) == {"p0", "p1"}
    assert len(client.calls) == 2

# ---------- taxonomy ----------
async def test_taxonomy_is_normalized_deduplicated_and_ends_with_otros():
    responder = Responder(taxonomy=[" Ahorro ", "ahorro", "Inversiones", "OTROS", "Cripto  Monedas", "Impuestos"])
    taxonomy = await build_taxonomy(make_posts(10), scripted(responder), SETTINGS)
    assert taxonomy == ["ahorro", "inversiones", "cripto monedas", "impuestos", "otros"]

async def test_taxonomy_has_at_most_nine_entries():
    responder = Responder(taxonomy=[f"tema {i}" for i in range(8)])
    taxonomy = await build_taxonomy(make_posts(10), scripted(responder), SETTINGS)
    assert len(taxonomy) == 9
    assert taxonomy[-1] == "otros"

def test_taxonomy_response_rejects_more_than_eight_topics():
    with pytest.raises(ValidationError):
        TaxonomyResponse(topics=[f"t{i}" for i in range(9)])

def test_taxonomy_sample_is_deterministic_spread_and_capped():
    posts = make_posts(200)
    sample = sample_for_taxonomy(posts)
    assert len(sample) == 60
    assert sample == sample_for_taxonomy(list(reversed(posts)))
    dates = [p.created_at for p in sample]
    assert min(dates) == min(p.created_at for p in posts)
    assert max(dates) == max(p.created_at for p in posts)
    assert len({p.id for p in sample}) == 60
    assert len(sample_for_taxonomy(make_posts(12))) == 12

async def test_taxonomy_prompt_sees_at_most_sixty_posts():
    responder = Responder()
    await build_taxonomy(make_posts(200), scripted(responder), SETTINGS)
    user = responder.taxonomy_calls[0].user
    assert sum(f"Post número {i} " in user for i in range(200)) == 60

# ---------- batch labeling ----------
async def test_sixty_posts_in_batches_of_25_make_three_calls_and_label_everything():
    posts = make_posts(60)
    responder = Responder()
    labels = await label_posts(posts, ["ahorro", "otros"], scripted(responder), SETTINGS, batch_size=25)
    assert sorted(len(ids) for ids in responder.label_calls) == [10, 25, 25]
    assert set(labels) == {p.id for p in posts}
    assert all(isinstance(label, PostLabel) for label in labels.values())

async def test_missing_ids_are_retried_once_and_unknown_ids_ignored():
    posts = make_posts(5)
    responder = Responder(drop_once={"p3"}, extra_ids=["ghost"])
    labels = await label_posts(posts, ["ahorro", "otros"], scripted(responder), SETTINGS, batch_size=25)
    assert set(labels) == {"p0", "p1", "p2", "p3", "p4"}
    assert responder.label_calls[1] == ["p3"]

def test_apply_labels_merges_without_touching_deterministic_fields():
    posts = make_posts(3)
    features = features_of(posts)
    labels = {"p0": PostLabel.model_validate(label_json("p0", sentiment=-0.4))}
    merged = apply_labels(features, labels)
    assert merged["p0"].topic == "ahorro"
    assert merged["p0"].tone == "informativo"
    assert merged["p0"].sentiment == -0.4
    assert merged["p0"].hook == "pregunta"
    assert merged["p0"].cta == "guardar"
    assert merged["p0"].model_dump(exclude=SEMANTIC) == features["p0"].model_dump(exclude=SEMANTIC)
    assert merged["p1"] == features["p1"]
    assert features["p0"].topic is None

# ---------- label_account (never raises on LLM failures) ----------
async def test_label_account_full_success():
    posts = make_posts(30)
    responder = Responder()
    result = await label_account(posts, features_of(posts), scripted(responder), SETTINGS)
    assert result.taxonomy == ["ahorro", "inversiones", "impuestos", "cripto", "humor", "otros"]
    assert result.coverage == 1.0
    assert result.errors == []
    assert all(f.topic == "ahorro" and f.hook == "pregunta" for f in result.features.values())

async def test_batch_failing_twice_leaves_none_labels_and_records_errors():
    posts = make_posts(60)
    features = features_of(posts)
    responder = Responder(fail_ids={"p30"})
    result = await label_account(posts, features, scripted(responder), SETTINGS, batch_size=25)
    failed_batch = next(ids for ids in responder.label_calls if "p30" in ids)
    assert len(failed_batch) == 25
    assert sum("p30" in ids for ids in responder.label_calls) == 2
    for post_id in failed_batch:
        assert result.features[post_id] == features[post_id]
    assert result.coverage == pytest.approx(35 / 60)
    assert result.errors

async def test_taxonomy_failure_falls_back_to_hashtags_and_still_labels_style():
    posts = [make_post(0, hashtags=["Ahorro"]), make_post(1), make_post(2, hashtags=["cripto", "btc"])]
    responder = Responder(fail_taxonomy=True, topic="otros")
    result = await label_account(posts, features_of(posts), scripted(responder), SETTINGS)
    assert result.taxonomy == []
    assert result.errors
    assert [result.features[p.id].topic for p in posts] == ["ahorro", None, "cripto"]
    assert all(result.features[p.id].tone == "informativo" for p in posts)

async def test_rate_limit_during_labeling_does_not_raise():
    posts = make_posts(5)
    client = ScriptedLLMClient([RateLimitedError("Muchas consultas."), RateLimitedError("Muchas consultas.")])
    result = await label_account(posts, features_of(posts), client, SETTINGS)
    assert result.errors
    assert result.coverage < 1

async def test_llm_disabled_makes_zero_calls():
    posts = make_posts(5)
    features = features_of(posts)
    client = ScriptedLLMClient([])
    result = await label_account(posts, features, client, replace(SETTINGS, enable_llm=False))
    assert client.calls == []
    assert result.features == features
    assert result.taxonomy == []
    assert result.coverage == 0.0

async def test_no_client_makes_no_calls_and_keeps_features():
    posts = make_posts(5)
    features = features_of(posts)
    result = await label_account(posts, features, None, SETTINGS)
    assert result.features == features
    assert result.coverage == 0.0

async def test_label_account_on_shared_fixture():
    snapshot = load_snapshot()
    posts = snapshot.posts
    features = {p.id: extract_deterministic(p, snapshot.trends) for p in posts}
    result = await label_account(posts, features, scripted(Responder()), SETTINGS)
    assert result.coverage == 1.0
    assert set(result.features) == {p.id for p in posts}

# ---------- prompts are cache-stable ----------
async def test_prompts_contain_no_dates_or_times():
    responder = Responder()
    client = scripted(responder)
    await label_account(make_posts(30), features_of(make_posts(30)), client, SETTINGS)
    systems = {call.system for call in client.calls}
    assert len(systems) == 2
    for text in [*systems, prompts.TAXONOMY_SYSTEM, prompts.LABEL_SYSTEM]:
        assert not re.search(r"\b20\d\d\b", text)
        assert not re.search(r"\b\d{1,2}:\d{2}\b", text)

def test_label_prompt_mentions_every_label():
    for label in [*TONE_LABELS, *HOOK_LABELS, *CTA_LABELS]:
        assert label in prompts.LABEL_SYSTEM
