"""
Manual check (not run in CI): label a snapshot's scorable posts with the real model and print the results.
Usage: OPENROUTER_API_KEY=... python src/ai/scripts/label_snapshot.py [snapshot.json] [max_posts]
Without a path it uses the shared fixture (40 posts).
"""
import asyncio
import logging
import sys
import time
from collections import Counter
from pathlib import Path
from eduhub_ai.config import load_settings
from eduhub_ai.features import extract_deterministic, select_scorable
from eduhub_ai.labeling import label_account
from eduhub_ai.llm.openrouter import OpenRouterClient
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.models import AccountSnapshot

def load(path: str | None) -> AccountSnapshot:
    """
    Load the snapshot at path, or the shared fixture.
    """
    if path is None:
        return load_snapshot()
    return AccountSnapshot.model_validate_json(Path(path).read_text(encoding="utf-8"))

async def main(path: str | None, max_posts: int) -> None:
    """
    Run the labeling passes on up to max_posts scorable posts and print taxonomy, coverage and labels.
    """
    snapshot = load(path)
    posts = select_scorable(snapshot.posts, snapshot.collected_at).scorable[:max_posts]
    features = {p.id: extract_deterministic(p, snapshot.trends) for p in posts}
    settings = load_settings()
    started = time.perf_counter()
    result = await label_account(posts, features, OpenRouterClient(settings), settings)
    print(f"@{snapshot.profile.handle}: {len(posts)} posts in {time.perf_counter() - started:.1f}s "
          f"model={settings.label_model} coverage={result.coverage:.0%}")
    print("taxonomy:", result.taxonomy)
    print("errors:", result.errors)
    for name in ("topic", "tone", "hook", "cta"):
        print(f"{name}:", dict(Counter(getattr(f, name) for f in result.features.values()).most_common()))
    for post in posts[:15]:
        f = result.features[post.id]
        print(f"- [{f.topic} | {f.tone} | {f.hook} | {f.cta} | {f.sentiment}] {' '.join(post.text.split())[:110]}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    args = sys.argv[1:]
    asyncio.run(main(args[0] if args else None, int(args[1]) if len(args) > 1 else 200))
