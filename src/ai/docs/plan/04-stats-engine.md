# Stage 04: Stats engine (KPIs, heatmap, segments, significance)

- **Status:** todo
- **Priority:** MUST
- **Depends on:** 02 (features + scores). Labels from stage 03 are optional inputs, and every function works with `None` labels.

## Goal

Exact, deterministic statistics that become the dashboard numbers **and** the evidence for insights: KPIs, the weekday × hour heatmap, best slots, segment stats with **bootstrap confidence intervals**, and a significance filter, so no "insight" rests on 2 lucky posts.

## Read first

- `../research.md` §4.3
- `src/shared/eduhub_shared/fakes.py` (`build_kpis`, `build_heatmap`, `build_segments`, `best_time_slots`: reuse or port these)
- `src/shared/eduhub_shared/models/analysis.py` (`AccountKPIs`, `TimeSlotStat`, `SegmentStat`)

## Design

- **Dependencies:** `numpy`, `scipy`.
- **Input type:** `list[AnalyzedPost]`, where unscorable posts have `score=None`. Stats use scorable posts only. KPIs (except rates) use all posts.
- **`stats/kpis.py`:** `build_kpis(posts: list[Post]) -> AccountKPIs`. Rates come from `metrics.aggregate_rates`.
- **`stats/timing.py`:**
  - `build_heatmap(...) -> list[TimeSlotStat]` (only slots that have posts; `avg_score` = **median** of the scores, documented);
  - `hour_block_stats(...)`: per hour block × weekday/weekend, used as insight evidence because raw cells are sparse; and
  - `best_time_slots(...)`: top 3 slots, preferring `post_count >= 2`.
- **`stats/segments.py`:**
  - `build_segments(posts) -> list[SegmentStat]` for every `SegmentDimension` (topic, media_type, length_bucket, tone, post_kind, hook, cta), skipping `None` values; and
  - `segment_details(...) -> list[SegmentDetail]`, an internal dataclass with `n`, `median_score`, `ci_low`, `ci_high`, `lift_vs_rest` and `p_value`.
- **`stats/significance.py`:**
  - `bootstrap_ci(values, stat=np.median, n_resamples=1000, seed=0, level=0.9)`;
  - `mann_whitney(group, rest) -> float` (p-value, two-sided); and
  - `is_significant(detail, min_n=3, alpha=0.1) -> bool`: true when n ≥ min_n and either the CI excludes 1.0 or p < alpha.

  A fixed seed means identical output on every run.

## Tests to write first (`src/ai/tests/test_stage_04_stats.py`) → STOP for approval

- KPIs on the fixture match `eduhub_shared.fakes.build_kpis` (same formulas): post count, period, posts per week, median impressions, aggregated rates.
- Heatmap: unique slots, counts sum to the number of scorable posts, `avg_score` is the median of that slot's scores.
- Best slots: at most 3. A slot with 1 post loses to a slot with 2+ posts and a slightly lower score.
- Segments:
  - one row per (dimension, value) present;
  - `None` values are skipped;
  - hook/cta dimensions appear when the labels exist and are absent when all are `None`.
- Bootstrap: deterministic with a seed, the CI contains the median, and the CI narrows as n grows.
- Significance:
  - a synthetic group with all scores ≈ 2.0 vs a rest ≈ 1.0 (n=10 each) is significant;
  - a group of 2 posts is never significant; and
  - identical distributions aren't significant.
- On the shared fixture snapshot: "presupuesto" is the best topic and is significant. "tarjetas" is the worst. This sanity-checks that the data's built-in story is recovered.

## Definition of done

- [ ] Tests green, plus ruff and style
- [ ] Every function is pure and deterministic (no clock, seeded randomness)
- [ ] Commit `ai: stage 04 stats engine`

## Handoff notes

_(fill in when done)_
