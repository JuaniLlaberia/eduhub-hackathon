"""
Model bake-off (research §10 D4), offline: cross-validated pairwise accuracy of every BAKEOFF_MODELS entry on
each account. Uses the saved reports from analyze_accounts.py (LLM labels included) when present, otherwise
analyzes the snapshots in template mode (deterministic features + hashtag topics only).
Usage: python src/ai/scripts/bakeoff.py
"""
import asyncio
import statistics
from pathlib import Path
from eduhub_ai.analyzer import HybridAnalyzer
from eduhub_ai.config import load_settings
from eduhub_ai.patterns import feature_row, pairwise_accuracy
from eduhub_ai.patterns.alternatives import BAKEOFF_MODELS
from eduhub_shared.models import AccountSnapshot, AnalysisReport

REAL_DATA = Path(__file__).resolve().parents[1] / "tests" / "data" / "real"
REPORTS = REAL_DATA / "reports"
SEEDS = (0, 1, 2)

def load_reports() -> tuple[list[AnalysisReport], str]:
    """
    Saved LLM reports if any, else template-mode reports computed now; plus a label for the source.
    """
    saved = sorted(REPORTS.glob("*.report.json"))
    if saved:
        return [AnalysisReport.model_validate_json(p.read_text(encoding="utf-8")) for p in saved], "saved reports"
    analyzer = HybridAnalyzer(load_settings({}), None)
    snapshots = [AccountSnapshot.model_validate_json(p.read_text(encoding="utf-8"))
                 for p in sorted(REAL_DATA.glob("*.json"))]
    return [asyncio.run(analyzer.analyze(s)) for s in snapshots], "template mode (no LLM labels)"

def evaluate(report: AnalysisReport) -> dict[str, float]:
    """
    Mean pairwise accuracy over SEEDS (different fold splits) for every model on one account.
    """
    scored = [p for p in report.posts if p.score is not None]
    rows = [feature_row(p.features) for p in scored]
    scores = [p.score or 0.0 for p in scored]
    return {name: statistics.fmean(pairwise_accuracy(factory, rows, scores, seed=seed) for seed in SEEDS)
            for name, factory in BAKEOFF_MODELS.items()}

def main() -> None:
    """
    Print the bake-off table (markdown), best model per account in bold.
    """
    reports, source = load_reports()
    names = list(BAKEOFF_MODELS)
    print(f"Source: {source}. 5-fold pairwise accuracy, mean of {len(SEEDS)} splits (0.5 = chance).\n")
    print("| Account | Scored | " + " | ".join(names) + " |")
    print("|---|---|" + "---|" * len(names))
    totals: dict[str, list[float]] = {name: [] for name in names}
    for report in reports:
        results = evaluate(report)
        best = max(results.values())
        cells = [f"**{v:.3f}**" if v == best else f"{v:.3f}" for v in results.values()]
        scored = sum(p.score is not None for p in report.posts)
        print(f"| @{report.profile.handle} | {scored} | " + " | ".join(cells) + " |")
        for name, value in results.items():
            totals[name].append(value)
    print("| **mean** | | " + " | ".join(f"{statistics.fmean(v):.3f}" for v in totals.values()) + " |")

if __name__ == "__main__":
    main()
