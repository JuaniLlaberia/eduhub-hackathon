# Stage 02: Deterministic features, post selection, score

- **Status:** done
- **Priority:** MUST
- **Depends on:** 00 (for the `hook`/`cta` fields; the code here leaves them `None`)

## Goal

Pure, deterministic functions (no LLM) that decide **which posts are scorable**, extract the **P1 features**, and compute the **performance score (option c)** for every post.

## Read first

- `../research.md` §4.2 (score options and hygiene rules) and §9 D2, D7
- `src/shared/eduhub_shared/metrics.py` (rates and length buckets: use these, don't re-implement)
- `src/shared/eduhub_shared/fakes.py` (`extract_features`, `relative_scores`: the logic to start from)
- `src/shared/eduhub_shared/models/analysis.py` (`PostFeatures`, `AnalyzedPost`)

## Design

- **`features/selection.py`:** `select_scorable(posts: list[Post], now: datetime, min_age: timedelta = timedelta(hours=48)) -> SelectionResult` with:
  - `scorable`: kind is original or quote, `impressions` > 0, and `created_at <= now - min_age`;
  - `excluded`: post id → reason (`"reply"`, `"repost"`, `"too_recent"`, `"no_impressions"`).

  `now` is injected, never read from the clock inside the function.
- **`features/deterministic.py`:** `extract_deterministic(post: Post, trends: list[Trend]) -> PostFeatures` with:
  - semantic fields left `None` (topic, tone, sentiment, hook, cta);
  - hour and weekday in `America/Argentina/Buenos_Aires`;
  - `length_bucket` from `metrics.length_bucket`;
  - question/emoji detection; and
  - `matches_trend`: case- and accent-insensitive match of the trend names, without `#`.

  Also `hour_block(hour: int) -> str` with the blocks `madrugada` 0–6, `mañana` 6–12, `mediodía` 12–15, `tarde` 15–19, `noche` 19–24.
- **`features/scoring.py`:** `score_posts(posts: list[Post]) -> dict[str, float | None]`:
  - `er_rel = ER / median(ER)` and `reach_rel = impressions / median(impressions)`, with medians **computed over scorable posts only**;
  - `score = sqrt(er_rel * reach_rel)` (geometric mean, where 1.0 = typical post);
  - `None` when there are no impressions or a median is 0.

  Document the formula in the module docstring, since it's referenced in the pitch.
- Add `MIN_SCORABLE_POSTS = 20` as a constant. The analyzer (stage 06) decides what to do below it.

## Tests to write first (`src/ai/tests/test_stage_02_features.py`) → STOP for approval

- **Selection:** a reply, a repost, a 10 h-old post and a no-impressions post are excluded with the right reasons. A 3-day-old original and a quote are scorable. A post exactly at the 48 h boundary counts as scorable.
- **Time:** a post at 2026-10-28T23:30Z is `hour_local=20`, `weekday=2` (Wednesday) in Argentina (UTC−3). `hour_block(20) == "noche"`, `hour_block(5) == "madrugada"`.
- **Features:** `length_bucket` matches `metrics.length_bucket`. `"¿Ahorrás?"` is a question. Emojis are detected. Trend `#Aguinaldo` matches the text "cobré el aguinaldo" (case/accent-insensitive). Semantic fields are `None`.
- **Scores:**
  - A post with the median ER and median reach scores 1.0.
  - Double the ER at median reach → √2.
  - Missing impressions → `None`.
  - All scores are ≥ 0.
  - One viral outlier doesn't change the other posts' scores by more than its effect on the medians (property: the medians are robust).
- **On the shared fixture snapshot:** every post gets features, and the scores of scorable posts aren't `None`.

## Definition of done

- [x] Tests green, plus ruff and style (141 passed: shared + stages 01–02)
- [x] No LLM imports in `features/` (asserted by a test)
- [x] Commit `ai: stage 02 features, selection, score`

## Handoff notes

- Built on 2026-10-31: `features/selection.py` (`select_scorable`, `SelectionResult`, `ExclusionReason`, `MIN_SCORABLE_POSTS = 20`), `features/deterministic.py` (`extract_deterministic`, `hour_block`, `is_question`, `matches_any_trend`), `features/scoring.py` (`score_posts`, formula in the module docstring).
- Tests: `src/ai/tests/test_stage_02_features.py`, approved by Juan. The real-snapshot test runs only when `tests/data/real/*.json` exist locally (git-ignored).
- Decisions beyond the plan:
  - Exclusion precedence: kind (reply/repost) → too_recent → no_impressions. Zero impressions count as no impressions.
  - `score_posts` takes the **scorable posts** (pass `selection.scorable`); medians come from those with impressions. Posts not passed in get no score (the analyzer sets `score=None` for them).
  - `is_question` ignores `?` inside URLs and also accepts an opening `¿`.
  - `matches_trend` is `None` when the snapshot has no trends; otherwise a whole-word, case/accent-insensitive match (so "Paro" does not match "comparo").
- Real data (collected 2026-10-31, `now = collected_at`): scorable posts bilinkis 70, mercadolibre 50, paulina_cocina 164, valearvejita 40 (all exclusions are replies). Median score 0.90–1.04, p90 1.8–5.9, max 3.5–13.3. Trend matches are ~0 because trends are from collection day and posts are older; don't expect `matches_trend` to drive insights.
