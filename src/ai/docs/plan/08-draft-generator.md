# Stage 08: Draft generator + `create_generator()`

- **Status:** done (not merged into `dev` yet)
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

- [x] Tests green, plus ruff and style (271 passed: shared + stages 01–08)
- [x] Manual check with the developer: 3 drafts for the fixture account. Do they sound like the creator? → `python src/ai/scripts/generate_drafts.py [snapshot.json] [count] [topic]`
- [ ] Merge into `dev`, and tell Mark that `create_generator()` is ready
- [x] Commit `ai: stage 08 draft generator`

## Handoff notes

- Built on 2026-10-31: `generation/schemas.py` (`DraftItem` with topic/tone/hook/cta labels, `DraftsResponse`), `generation/prompts.py` (`GENERATOR_SYSTEM`, `generator_user`, `retry_note`), `generation/generator.py` (`LLMDraftGenerator`, `next_slot_after`, `default_scorer`, `draft_features`), `src/ai/scripts/generate_drafts.py` (analyze + generate, manual).
- Tests: `src/ai/tests/test_stage_08_generator.py`, approved by Juan (code was written before approval at the developer's request).
- `create_generator()`: `LLMDraftGenerator` when the LLM is available, **`FakeDraftGenerator` without a key or with `AI_ENABLE_LLM=0`** (the approved stage 06 test runs `check_generator(create_generator())` with no key, and the backend needs a working endpoint). Inside the LLM generator there is no template fallback: LLM failures → `GenerationError("No pudimos generar borradores…")`; `RateLimitedError` propagates (429).
- Decisions beyond the plan:
  - The scorer takes the draft's `PostFeatures` (deterministic features of the text as if posted at its suggested time, plus the LLM's topic/tone/hook/CTA labels), not just the text. Default: refit ridge from `report.posts` (`fit_from_report`) and `predict`; else the median score of the draft's topic segment; else `None`. Scorer errors give `None`, never a failed generation.
  - Drafts are spread over the best slots: draft *i* gets `best_time_slots[i % n]` (draft 0 = best slot).
  - Unknown `recommendation_id` falls back to the top-priority recommendation (no error). `based_on_insight_ids` = the recommendation's insights, else the top two.
  - Trends: top 3 by rank; the prompt says to use one only if it fits.
  - Writer model + `AI_WRITER_REASONING`, temperature 0.8. Dedupe is case/whitespace-insensitive; the single retry asks only for the missing drafts and lists the existing ones.
- First real run (2026-10-31, paulina_cocina): analysis 22.6 s + drafts 10.9 s; voice close (voseo, her "Si hay X…" pattern). Fixed after it: (1) drafts declare their intended `media` (text/photo/video/gif) and the score uses it — before, video recipes were scored as text-only (0.7x on an account where text is 0.4x); (2) the default topic needs ≥ 3 posts (a 1-post topic had won, so all drafts were about vegetables instead of "postres dulces"); (3) the placeholder rule covers only statistics/studies/news/quotes, so practical details (cooking times) are no longer "[dato]".
- Second real run after the fixes: all three drafts on desserts, her sign-off ("Bai los tkm 💞") and "Si tenés X, ya tenés hecha…" pattern, scores 1.4–1.9x for video desserts, no placeholders; analysis 13.0 s + drafts 14.1 s.
- **Test caveat:** if `OPENROUTER_API_KEY` is exported in the shell that runs pytest, the stage 06 factory test builds the real generator and makes a real call. Run pytest without the env loaded.
