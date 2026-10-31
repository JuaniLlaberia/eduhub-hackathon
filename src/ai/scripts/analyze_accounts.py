"""
Manual evaluation run (not in CI): analyze every real snapshot with the configured pipeline, save the reports
(git-ignored, next to the snapshots) and print latency, LLM calls, tokens and cost per account. Also writes a
30-label sample to grade by hand (labels_review.md).
Usage: python src/ai/scripts/analyze_accounts.py [snapshot.json ...]
"""
import asyncio
import logging
import random
import sys
import time
from pathlib import Path
from eduhub_ai import create_analyzer
from eduhub_shared.models import AccountSnapshot, AnalysisReport

REAL_DATA = Path(__file__).resolve().parents[1] / "tests" / "data" / "real"
REPORTS = REAL_DATA / "reports"
REVIEW_SAMPLE = 30

def analyze(path: Path) -> tuple[AnalysisReport, list[str]]:
    """
    Analyze one snapshot, save its report and return it with a markdown table row of measurements.
    """
    snapshot = AccountSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
    analyzer = create_analyzer()
    started = time.perf_counter()
    report = asyncio.run(analyzer.analyze(snapshot))
    elapsed = time.perf_counter() - started
    (REPORTS / f"{path.stem}.report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    usage = getattr(getattr(analyzer, "client", None), "usage", None)
    scored = sum(p.score is not None for p in report.posts)
    labeled = sum(p.features.tone is not None for p in report.posts if p.score is not None)
    row = [
        f"@{snapshot.profile.handle}", str(len(report.posts)), str(scored), f"{labeled / max(scored, 1):.0%}",
        str(len(report.insights)), f"{elapsed:.1f} s",
        str(usage.calls) if usage else "-", str(usage.failures) if usage else "-",
        f"{usage.prompt_tokens:,} / {usage.completion_tokens:,}" if usage else "-",
        f"${usage.cost:.4f}" if usage and usage.cost else "-",
    ]
    return report, row

def review_sample(reports: list[AnalysisReport]) -> str:
    """
    Markdown table of REVIEW_SAMPLE labeled posts (seeded) with an empty column to grade each one.
    """
    labeled = [(r.profile.handle, p) for r in reports for p in r.posts if p.features.tone is not None]
    sample = random.Random(0).sample(labeled, min(REVIEW_SAMPLE, len(labeled)))
    lines = ["# Label review (grade each row: ok / topic / tone / hook / cta)", "",
             "| Account | Post | Topic | Tone | Hook | CTA | Sentiment | OK? |", "|---|---|---|---|---|---|---|---|"]
    for handle, item in sample:
        f = item.features
        text = " ".join(item.post.text.split())[:160].replace("|", "/")
        lines.append(f"| @{handle} | {text} | {f.topic} | {f.tone} | {f.hook} | {f.cta} | {f.sentiment} |  |")
    return "\n".join(lines) + "\n"

def main(paths: list[Path]) -> None:
    """
    Analyze each snapshot in turn and print the measurements table.
    """
    REPORTS.mkdir(parents=True, exist_ok=True)
    header = ["Account", "Posts", "Scored", "Labeled", "Insights", "Time", "LLM calls", "Failed", "Tokens in / out",
              "Cost"]
    rows, reports = [], []
    for path in paths:
        report, row = analyze(path)
        reports.append(report)
        rows.append(row)
        print(" | ".join(row), flush=True)
    (REPORTS / "labels_review.md").write_text(review_sample(reports), encoding="utf-8")
    print("\n| " + " | ".join(header) + " |\n|" + "---|" * len(header))
    for row in rows:
        print("| " + " | ".join(row) + " |")
    print(f"\nReports and labels_review.md written to {REPORTS}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    given = [Path(p) for p in sys.argv[1:]]
    main(given or sorted(REAL_DATA.glob("*.json")))
