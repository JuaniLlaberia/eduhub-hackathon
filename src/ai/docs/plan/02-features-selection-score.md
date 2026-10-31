# Stage 02: Deterministic features, post selection, score

- **Status:** todo
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

- [ ] Tests green, plus ruff and style
- [ ] No LLM imports in `features/`
- [ ] Commit `ai: stage 02 features, selection, score`

## Handoff notes

_(fill in when done)_
