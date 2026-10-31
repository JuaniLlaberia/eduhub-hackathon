# Stage 08: Draft generator + `create_generator()`

- **Status:** todo
- **Priority:** WANTED
- **Depends on:** 06 (07 optional, for `estimated_score`)

## Goal

Generate `count` post drafts **in the creator's voice**, based on their insights, a requested topic or recommendation, and the current trends. Each draft comes with a rationale, a **suggested time** (next best slot) and an **estimated score**. The pitch line: "lo genera la IA y lo evalúa tu propio modelo".

## Read first

- `src/shared/eduhub_shared/interfaces.py` (`DraftGenerator`) and `testing.check_generator`
- `src/shared/eduhub_shared/models/generation.py` (`DraftRequest`, `Draft`)
- `src/shared/eduhub_shared/fakes.py` (`FakeDraftGenerator`, `next_slot_after`)
- `../research.md` §4.5

## Design

- **Input:** `generate(request, report, trends)`. The generator **only receives the report**, not the snapshot. Voice examples are the top 5–8 posts by score from `report.posts`.
- **`generation/prompts.py`:** es-AR system prompt:
  - imitate the voice and format of the examples (length, emojis, hashtags, voseo);
  - one idea per draft;
  - at most 280 characters unless the examples are longer;
  - no invented facts or figures about the world, and no political, medical or financial promises; and
  - vary the hook and CTA across drafts, using the account's best hook/CTA when known.

  Inputs: the examples, the selected recommendation or insight (from `recommendation_id` or the best one), the requested topic or the best topic, at most 3 relevant trends, and `request.instructions`.
- **`generation/generator.py`:** `LLMDraftGenerator(settings, client, clock, scorer: Callable[[str], float | None] | None)`. The response schema has `drafts[]` with `text`, `rationale` and `hook`/`cta` labels.
  - Post-process: trim, dedupe, enforce `count` (one retry if fewer come back).
  - `suggested_time` = `next_slot_after(clock(), best_slot)`.
  - `estimated_score` comes from the scorer: by default, refit ridge with `patterns.ridge.fit_from_report(report)` (stage 07), then `predict` on the draft's deterministic features + LLM-provided labels. Otherwise (stage 07 not done, or not enough data) use the segment-based estimate (median score of the draft's topic), or `None`.
  - `based_on_insight_ids` = the insights used.
- **Failure handling:** `GenerationError` with an es-AR message (the backend maps it to 500/429). There's no template fallback for drafts: the backend's `/features` can disable generation instead.
- **`create_generator()`** in `eduhub_ai/__init__.py`.

## Tests to write first (`src/ai/tests/test_stage_08_generator.py`) → STOP for approval

- `await check_generator(LLMDraftGenerator(... ScriptedLLMClient ...))` passes (contract test, `count=3`).
- The prompt contains the top posts as examples and the selected recommendation text when `recommendation_id` is given. It includes trends only up to 3.
- Fewer drafts than `count` → one retry. Still fewer → `GenerationError`.
- Duplicate drafts are removed.
- `suggested_time` is in the future and falls on the best slot in Argentina time.
- `estimated_score` uses the injected scorer when present, and the segment estimate otherwise.
- An LLM exception → `GenerationError` with an es-AR message.

## Definition of done

- [ ] Tests green, plus ruff and style
- [ ] Manual check with the developer: 3 drafts for the fixture account. Do they sound like the creator?
- [ ] Merge into `dev`, and tell Mark that `create_generator()` is ready
- [ ] Commit `ai: stage 08 draft generator`

## Handoff notes

_(fill in when done)_
