"""
Stage 06: HybridAnalyzer (full pipeline) and the contract factories. The scripted LLM below answers the
taxonomy, label-batch and writer calls from the prompts themselves, so it works on any snapshot.
"""
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
import pytest
from eduhub_ai import create_analyzer, create_generator, create_simulator
from eduhub_ai.analyzer import ENGINE, HybridAnalyzer
from eduhub_ai.config import load_settings
from eduhub_ai.insights.writer import WriterResponse
from eduhub_ai.labeling.schemas import LabelBatchResponse, TaxonomyResponse
from eduhub_ai.llm.client import LLMCall, LLMError
from eduhub_ai.llm.openrouter import OpenRouterClient
from eduhub_ai.llm.scripted import ScriptedLLMClient
from eduhub_shared.errors import AnalysisError
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.interfaces import Analyzer, DraftGenerator
from eduhub_shared.models import AccountSnapshot, PostKind, SegmentDimension
from eduhub_shared.testing import check_analyzer, check_generator

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=UTC)
SETTINGS = load_settings({})
TAXONOMY = ["presupuesto", "ahorro", "sueldo", "inversiones", "tarjetas"]
POST_LINE = re.compile(r'^\{"id": .*\}$', re.MULTILINE)
REAL_DATA = Path(__file__).parent / "data" / "real"
AI_ENV = ("OPENROUTER_API_KEY", "AI_ENABLE_LLM", "AI_LABEL_MODEL", "AI_WRITER_MODEL", "AI_FALLBACK_MODELS")

class FixtureLLM:
    """
    Answers every pipeline call from its prompt; can fail labeling, the writer, or crash with a bug.
    """
    def __init__(self, fail_labels: bool = False, fail_writer: bool = False, crash: bool = False) -> None:
        self.fail_labels = fail_labels
        self.fail_writer = fail_writer
        self.crash = crash
        self.schemas: list[str] = []

    def __call__(self, call: LLMCall) -> str:
        self.schemas.append(call.schema.__name__)
        if self.crash:
            raise RuntimeError("unexpected bug")
        if call.schema is TaxonomyResponse:
            if self.fail_labels:
                raise LLMError("taxonomy down")
            return json.dumps({"topics": TAXONOMY})
        if issubclass(call.schema, LabelBatchResponse):
            if self.fail_labels:
                raise LLMError("labels down")
            return self.labels(call.user)
        assert issubclass(call.schema, WriterResponse)
        if self.fail_writer:
            raise LLMError("writer down")
        return self.texts(call.user)

    def labels(self, user: str) -> str:
        posts = [json.loads(line) for line in POST_LINE.findall(user)]
        labels = []
        for post in posts:
            text = post["texto"].lower()
            topic = next((t for t in TAXONOMY if t in text), "otros")
            labels.append({"post_id": post["id"], "topic": topic, "tone": "informativo", "sentiment": 0.2,
                           "hook": "pregunta" if text.startswith("¿") else "dato", "cta": "ninguno"})
        return json.dumps({"labels": labels}, ensure_ascii=False)

    def texts(self, user: str) -> str:
        payload = json.loads(user.split("\n", 1)[1].split("\n\n")[0])
        insights = [
            {"category": "topic" if f["id"].startswith("seg:topic") else "other", "title": f["label"],
             "description": f"Rinde {f['numbers']['mediana']} tu post típico en {f['numbers']['posts']} posts.",
             "evidence_ids": [f["id"]], "impact": "high", "related_post_ids": []}
            for f in payload["findings"][:3]
        ]
        recommendations = [{"category": i["category"], "action": "Publicá más de esto.", "rationale": "Rinde más.",
                            "priority": n + 1, "insight_index": [n]} for n, i in enumerate(insights)]
        explanations = [{"post_id": p["id"], "text": f"Rindió {p['score']} tu post típico."}
                        for p in payload["top_posts"]]
        return json.dumps({"insights": insights, "recommendations": recommendations, "explanations": explanations,
                           "summary": "Tu cuenta tiene patrones claros."}, ensure_ascii=False)

def scripted(llm: FixtureLLM | None = None) -> ScriptedLLMClient:
    return ScriptedLLMClient([llm or FixtureLLM()] * 60)

def analyzer(client: ScriptedLLMClient | None = None, clock: datetime = NOW) -> HybridAnalyzer:
    return HybridAnalyzer(SETTINGS, client, clock=lambda: clock)

def segment_dimensions(report) -> set[SegmentDimension]:
    return {s.dimension for s in report.segments}

def with_unscorable_posts(snapshot: AccountSnapshot) -> AccountSnapshot:
    base = snapshot.posts[-1]
    extra = [
        base.model_copy(update={"id": "reply-1", "kind": PostKind.REPLY,
                                "created_at": base.created_at - timedelta(days=1)}),
        base.model_copy(update={"id": "repost-1", "kind": PostKind.REPOST,
                                "created_at": base.created_at - timedelta(days=2)}),
    ]
    return snapshot.model_copy(update={"posts": [*snapshot.posts, *extra]})

# ---------- contract ----------
async def test_contract_with_scripted_llm():
    llm = FixtureLLM()
    report = await check_analyzer(analyzer(scripted(llm)))
    assert report.engine == ENGINE == "hybrid-v1"
    assert {"TaxonomyResponse", "LabelBatchResponse", "WriterResponse"} <= set(llm.schemas)
    assert {SegmentDimension.TOPIC, SegmentDimension.TONE, SegmentDimension.HOOK} <= segment_dimensions(report)
    assert report.insights
    assert report.summary == "Tu cuenta tiene patrones claros."

async def test_contract_in_template_mode_without_client():
    report = await check_analyzer(analyzer(None))
    assert report.engine == "hybrid-v1"
    assert report.insights
    assert report.recommendations
    assert report.summary.startswith("Analizamos 40 posts de @")
    topics = [s for s in report.segments if s.dimension == SegmentDimension.TOPIC]
    assert topics[0].value == "presupuesto"
    assert SegmentDimension.TONE not in segment_dimensions(report)

async def test_labeling_failure_still_produces_a_report():
    report = await check_analyzer(analyzer(scripted(FixtureLLM(fail_labels=True))))
    dimensions = segment_dimensions(report)
    assert SegmentDimension.TONE not in dimensions
    assert SegmentDimension.HOOK not in dimensions
    assert SegmentDimension.CTA not in dimensions
    assert SegmentDimension.MEDIA_TYPE in dimensions
    assert SegmentDimension.LENGTH_BUCKET in dimensions
    assert SegmentDimension.TOPIC in dimensions  # hashtag fallback
    assert report.summary == "Tu cuenta tiene patrones claros."

async def test_writer_failure_uses_template_texts():
    report = await check_analyzer(analyzer(scripted(FixtureLLM(fail_writer=True))))
    assert report.insights
    assert report.insights[0].id == "ins-1"
    assert report.summary.startswith("Analizamos 40 posts de @")

# ---------- posts and segments ----------
async def test_unscorable_posts_are_in_the_report_without_score_and_out_of_segments():
    snapshot = with_unscorable_posts(load_snapshot())
    report = await check_analyzer(analyzer(None), snapshot)
    by_id = {p.post.id: p for p in report.posts}
    too_recent = snapshot.posts[0]
    assert too_recent.created_at > snapshot.collected_at - timedelta(hours=48)
    for post_id in ("reply-1", "repost-1", too_recent.id):
        assert by_id[post_id].score is None
    scorable = sum(p.score is not None for p in report.posts)
    media = [s for s in report.segments if s.dimension == SegmentDimension.MEDIA_TYPE]
    assert sum(s.post_count for s in media) == scorable == 39
    kinds = {s.value for s in report.segments if s.dimension == SegmentDimension.POST_KIND}
    assert kinds <= {"original", "quote"}

async def test_top_and_bottom_posts_have_explanations():
    report = await analyzer(None).analyze(load_snapshot())
    scored = sorted((p for p in report.posts if p.score is not None), key=lambda p: (-(p.score or 0), p.post.id))
    assert all(p.explanation for p in scored[:5])
    assert all(p.explanation for p in scored[-5:])
    assert all(p.explanation is None for p in report.posts if p.score is None)

# ---------- errors ----------
async def test_too_few_scorable_posts_raise_analysis_error_in_spanish():
    snapshot = load_snapshot()
    small = snapshot.model_copy(update={"posts": snapshot.posts[:11]})
    with pytest.raises(AnalysisError) as info:
        await analyzer(None).analyze(small)
    assert "20 posts" in info.value.message
    with pytest.raises(AnalysisError):
        await analyzer(None).analyze(snapshot.model_copy(update={"posts": []}))

async def test_unexpected_exception_is_wrapped_in_analysis_error():
    with pytest.raises(AnalysisError) as info:
        await analyzer(scripted(FixtureLLM(crash=True))).analyze(load_snapshot())
    assert info.value.message == "No pudimos analizar la cuenta. Probá de nuevo."

# ---------- progress ----------
async def test_progress_is_non_decreasing_and_ends_high():
    progress: list[tuple[float, str]] = []

    async def on_progress(value: float, message: str) -> None:
        progress.append((value, message))

    await analyzer(scripted()).analyze(load_snapshot(), on_progress)
    values = [v for v, _ in progress]
    assert values == sorted(values)
    assert values[-1] >= 0.8
    assert all(0 <= v <= 1 and m for v, m in progress)
    assert progress[0] == (0.10, "Leyendo tus posts")

# ---------- determinism and ids ----------
async def test_same_input_same_report_and_new_clock_new_id():
    snapshot = load_snapshot()
    first = await analyzer(scripted()).analyze(snapshot)
    second = await analyzer(scripted()).analyze(snapshot)
    assert first.model_dump_json() == second.model_dump_json()
    later = await analyzer(scripted(), clock=NOW + timedelta(seconds=1)).analyze(snapshot)
    assert later.id != first.id
    assert first.generated_at == NOW

# ---------- factories ----------
def clear_ai_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in AI_ENV:
        monkeypatch.delenv(name, raising=False)

def test_create_analyzer_with_empty_env_is_template_mode(monkeypatch):
    clear_ai_env(monkeypatch)
    created = create_analyzer()
    assert isinstance(created, Analyzer)
    assert created.client is None

def test_create_analyzer_with_key_builds_openrouter_client_without_network(monkeypatch):
    clear_ai_env(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    assert isinstance(create_analyzer().client, OpenRouterClient)
    monkeypatch.setenv("AI_ENABLE_LLM", "0")
    assert create_analyzer().client is None

async def test_create_generator_does_not_raise_and_honours_the_contract():
    generator = create_generator()
    assert isinstance(generator, DraftGenerator)
    await check_generator(generator)

def test_create_simulator_is_disabled():
    assert create_simulator() is None

# ---------- real snapshots (local only) ----------
@pytest.mark.skipif(not list(REAL_DATA.glob("*.json")), reason="real snapshots are git-ignored; copy them locally")
@pytest.mark.parametrize("path", sorted(REAL_DATA.glob("*.json")), ids=lambda p: p.stem)
async def test_real_snapshots_in_template_mode(path):
    snapshot = AccountSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    report = await check_analyzer(analyzer(None), snapshot)
    assert report.insights
