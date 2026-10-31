"""
Audience sandbox on the whole ENCC pool (492 personas) vs. samples of 200 (the API cap), calling the simulator
directly. SimulationRequest caps audience_size at 200, so the full-pool request is built with model_construct
(validation skipped in this script only; the contract is unchanged). Usage: python sandbox_full.py
"""
import asyncio
import json
import time
from itertools import combinations
from pathlib import Path
from eduhub_ai import create_simulator
from eduhub_ai.sandbox.personas import load_personas, sample_personas
from eduhub_ai.sandbox.simulator import ACTIVE, LLMAudienceSimulator, weighted_rate
from eduhub_shared.models import AudienceFilters, SimulationRequest, SimulationResult

HERE = Path(__file__).parent
REPO = HERE.parents[3]
BRIEFS = REPO / "src/ai/docs/results/2026-10-31-e2e/briefs"
OUT = REPO / "src/ai/tests/data/real/reports/e2e-2026-10-31"
FULL_REPEATS = 2
SEEDS = [0, 1, 2]
USAGE_KEYS = ("calls", "failures", "prompt_tokens", "completion_tokens", "cost")

def variant_sets() -> dict[str, list[str]]:
    """
    Set A: the 3 drafts generated for paulina_cocina with her brief (real use case).
    Set B: the 2 default variants of scripts/simulate.py (compares with the stage 09 runs).
    """
    paulina = json.loads((OUT / "e2e_results.json").read_text())["cases"]
    drafts = next(c for c in paulina if c["handle"] == "paulina_cocina" and c["brief"])["drafts"]["texts"]
    return {
        "A_paulina_brief_drafts": drafts[:3],
        "B_simulate_defaults": [
            "¿Cuánto gastás por mes en delivery? Hice la cuenta y me asusté 😳",
            "Armé una planilla gratis para controlar tus gastos del mes. Te la dejo acá 👇",
        ],
    }

def ranking(rates: list[float]) -> list[int]:
    """
    Variant indexes from best to worst.
    """
    return sorted(range(len(rates)), key=lambda i: (-rates[i], i))

def summarize(result: SimulationResult, elapsed: float, used: dict) -> dict:
    """
    The numbers we compare across runs.
    """
    rates = [v.interaction_rate for v in result.variants]
    expected = len(result.personas) * len(result.variants)
    return {
        "personas": len(result.personas), "reactions": len(result.reactions), "expected": expected,
        "missing_reactions": expected - len(result.reactions),
        "rates": [round(r, 4) for r in rates], "ranking": ranking(rates), "best": result.best_variant_index,
        "counts": [{k.value: n for k, n in v.reaction_counts.items() if n} for v in result.variants],
        "seconds": round(elapsed, 2), **used, "summary": result.summary,
    }

def subset_rates(result: SimulationResult, ids: set[str], n_variants: int) -> list[float]:
    """
    Weighted interaction rates of a full-pool run restricted to the personas in ids (no new LLM calls).
    """
    personas = [p for p in result.personas if p.id in ids]
    reactions = [r for r in result.reactions if r.persona_id in ids]
    own = [[r for r in reactions if r.variant_index == i] for i in range(n_variants)]
    return [round(weighted_rate(personas, rs), 4) for rs in own]

def agreement(a: SimulationResult, b: SimulationResult, n_variants: int) -> float:
    """
    Share of (persona, variant) pairs where two runs on the same personas agree on active vs. passive.
    """
    def key(result: SimulationResult) -> dict[tuple[str, int], bool]:
        """
        Active-or-not per (persona, variant).
        """
        return {(r.persona_id, r.variant_index): r.reaction in ACTIVE for r in result.reactions}

    ka, kb = key(a), key(b)
    common = set(ka) & set(kb)
    return round(sum(ka[k] == kb[k] for k in common) / len(common), 4) if common else 0.0

def paired_wins(result: SimulationResult, n_variants: int) -> dict:
    """
    For each pair of variants, weighted share of personas active on one but not the other (who prefers whom).
    """
    weights = {p.id: p.weight for p in result.personas}
    active = {(r.persona_id, r.variant_index): r.reaction in ACTIVE for r in result.reactions}
    out = {}
    for i, j in combinations(range(n_variants), 2):
        wi = sum(w for pid, w in weights.items() if active.get((pid, i)) and active.get((pid, j)) is False)
        wj = sum(w for pid, w in weights.items() if active.get((pid, j)) and active.get((pid, i)) is False)
        total = sum(weights.values())
        out[f"v{i + 1}_vs_v{j + 1}"] = {f"only_v{i + 1}": round(wi / total, 4), f"only_v{j + 1}": round(wj / total, 4)}
    return out

async def run(
    simulator: LLMAudienceSimulator, variants: list[str], size: int, seed: int
) -> tuple[SimulationResult, float, dict]:
    """
    One simulation with the given seed, measuring time and usage delta.
    """
    simulator.seed = seed
    before = vars(simulator.client.usage).copy()
    request = (SimulationRequest.model_construct(variants=variants, audience_size=size, filters=AudienceFilters(),
                                                 context=None, handle=None)
               if size > 200 else SimulationRequest(variants=variants, audience_size=size))
    started = time.perf_counter()
    result = await simulator.simulate(request)
    elapsed = time.perf_counter() - started
    after = vars(simulator.client.usage)
    used = {k: round(after[k] - before[k], 6) for k in USAGE_KEYS}
    return result, elapsed, used

async def main() -> None:
    """
    Per variant set: FULL_REPEATS runs on all 492 personas, then one run of 200 per seed; then compare.
    """
    simulator = create_simulator()
    assert simulator is not None, "sandbox disabled (needs OPENROUTER_API_KEY and personas.json)"
    pool = load_personas()
    report: dict = {"pool_size": len(pool), "label_model": simulator.settings.label_model,
                    "label_reasoning": simulator.settings.label_reasoning,
                    "max_concurrency": simulator.settings.max_concurrency, "sets": {}}
    for name, variants in variant_sets().items():
        n = len(variants)
        full = []
        for k in range(FULL_REPEATS):
            result, elapsed, used = await run(simulator, variants, len(pool), 0)
            full.append(result)
            rates = summarize(result, elapsed, used)["rates"]
            print(f"{name} full#{k + 1}: {rates} {elapsed:.1f}s ${used['cost']:.4f} "
                  f"failures={used['failures']}", flush=True)
            report["sets"].setdefault(name, {"variants": variants, "full": [], "sample200": []})
            report["sets"][name]["full"].append({**summarize(result, elapsed, used),
                                                 "paired": paired_wins(result, n)})
        for seed in SEEDS:
            result, elapsed, used = await run(simulator, variants, 200, seed)
            ids = {p.id for p in sample_personas(pool, AudienceFilters(), 200, seed)}
            entry = {"seed": seed, **summarize(result, elapsed, used),
                     "same_200_in_full_runs": [subset_rates(f, ids, n) for f in full]}
            report["sets"][name]["sample200"].append(entry)
            print(f"{name} 200 seed={seed}: {entry['rates']} (same personas in full runs: "
                  f"{entry['same_200_in_full_runs']}) {elapsed:.1f}s ${used['cost']:.4f}", flush=True)
        report["sets"][name]["full_run_agreement"] = agreement(full[0], full[1], n) if len(full) > 1 else None
    (OUT / "sandbox_full_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    asyncio.run(main())
