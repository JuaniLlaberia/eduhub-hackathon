"""
Manual check (not run in CI): run features, scores, labels, stats and the insight writer on a snapshot and
print the texts. Without OPENROUTER_API_KEY (or with AI_ENABLE_LLM=0) it prints the template texts.
Usage: python src/ai/scripts/write_insights.py [snapshot.json]
"""
import asyncio
import logging
import sys
import time
from pathlib import Path
from eduhub_ai.config import load_settings
from eduhub_ai.features import extract_deterministic, score_posts, select_scorable
from eduhub_ai.insights import build_evidence, write_texts
from eduhub_ai.labeling import label_account
from eduhub_ai.llm.openrouter import OpenRouterClient
from eduhub_ai.stats import best_time_slots, build_heatmap, build_kpis
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.metrics import compute_rates
from eduhub_shared.models import AccountSnapshot, AnalyzedPost

def load(path: str | None) -> AccountSnapshot:
    """
    Load the snapshot at path, or the shared fixture.
    """
    if path is None:
        return load_snapshot()
    return AccountSnapshot.model_validate_json(Path(path).read_text(encoding="utf-8"))

async def main(path: str | None) -> None:
    """
    Run the pipeline up to the writer and print the texts with their source.
    """
    snapshot = load(path)
    settings = load_settings()
    client = OpenRouterClient(settings) if settings.openrouter_api_key and settings.enable_llm else None
    started = time.perf_counter()
    scorable = select_scorable(snapshot.posts, snapshot.collected_at).scorable
    scores = score_posts(scorable)
    features = {p.id: extract_deterministic(p, snapshot.trends) for p in snapshot.posts}
    labeled = await label_account(scorable, features, client, settings)
    posts = [AnalyzedPost(post=p, features=labeled.features[p.id], rates=compute_rates(p.metrics),
                          score=scores.get(p.id)) for p in snapshot.posts]
    pack = build_evidence(snapshot.profile, build_kpis(snapshot.posts), posts, best_time_slots(build_heatmap(posts)))
    texts = await write_texts(pack, client, settings)
    print(f"@{snapshot.profile.handle}: {time.perf_counter() - started:.1f}s, labels {labeled.coverage:.0%}, "
          f"texts from {texts.source}, {len(pack.findings)} findings")
    print("errors:", [*labeled.errors, *texts.errors])
    print("\nRESUMEN:", texts.summary)
    for insight in texts.insights:
        print(f"\n[{insight.category.value} · {insight.impact.value} · conf {insight.confidence}] {insight.title}")
        print("  ", insight.description)
        print("   evidencia:", "; ".join(f"{e.label}: {e.value}" for e in insight.evidence))
    print()
    for rec in texts.recommendations:
        print(f"{rec.priority}. {rec.action} ({rec.rationale})")
    print()
    for post_id, text in list(texts.explanations.items())[:4]:
        print(f"- {post_id}: {text}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))
