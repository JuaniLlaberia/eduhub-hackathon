"""
Manual check (not run in CI): analyze a snapshot with the real pipeline, then generate drafts from that report
and print them with their suggested time and estimated score. Needs OPENROUTER_API_KEY for real drafts.
Usage: python src/ai/scripts/generate_drafts.py [snapshot.json] [count] [topic] [--brief brief.json]
"""
import asyncio
import logging
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo
from eduhub_ai import create_analyzer, create_generator
from eduhub_shared.fixtures import load_snapshot
from eduhub_shared.models import AccountSnapshot, CreatorContext, DraftRequest

AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

def load(path: str | None) -> AccountSnapshot:
    """
    Load the snapshot at path, or the shared fixture.
    """
    if path is None:
        return load_snapshot()
    return AccountSnapshot.model_validate_json(Path(path).read_text(encoding="utf-8"))

async def main(path: str | None, count: int, topic: str | None, brief: CreatorContext | None) -> None:
    """
    Analyze (with the creator brief, if given), then generate count drafts (optionally about topic) and print them.
    """
    snapshot = load(path)
    if brief is not None:
        snapshot = snapshot.model_copy(update={"context": brief})
        print("BRIEF:", brief.model_dump(mode="json", exclude_defaults=True))
    started = time.perf_counter()
    report = await create_analyzer().analyze(snapshot)
    analyzed = time.perf_counter()
    generator = create_generator()
    request = DraftRequest(handle=snapshot.profile.handle, topic=topic, count=count)
    drafts = await generator.generate(request, report, snapshot.trends)
    elapsed = time.perf_counter() - analyzed
    print(f"@{snapshot.profile.handle}: analysis {analyzed - started:.1f}s, drafts {elapsed:.1f}s "
          f"({type(generator).__name__})")
    print("\nVOZ (top posts):")
    for item in sorted((p for p in report.posts if p.score is not None), key=lambda p: -(p.score or 0))[:3]:
        print(f"  [{item.score:.1f}x] {' '.join(item.post.text.split())[:140]}")
    for draft in drafts:
        when = draft.suggested_time.astimezone(AR_TZ).strftime("%a %d/%m %H:%M") if draft.suggested_time else "-"
        score = f"{draft.estimated_score:.2f}x" if draft.estimated_score is not None else "-"
        print(f"\n[{when} · estimado {score} · insights {draft.based_on_insight_ids}]")
        print(f"{draft.text}\n  → {draft.rationale}")

def pop_brief(args: list[str]) -> CreatorContext | None:
    """
    Remove "--brief path" from args and load that creator brief (contract CreatorContext), if given.
    """
    if "--brief" not in args:
        return None
    index = args.index("--brief")
    path = Path(args[index + 1])
    del args[index:index + 2]
    return CreatorContext.model_validate_json(path.read_text(encoding="utf-8"))

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("eduhub_ai.llm").setLevel(logging.INFO)
    args = sys.argv[1:]
    brief = pop_brief(args)
    count = int(args[1]) if len(args) > 1 else 3
    asyncio.run(main(args[0] if args else None, count, args[2] if len(args) > 2 else None, brief))
