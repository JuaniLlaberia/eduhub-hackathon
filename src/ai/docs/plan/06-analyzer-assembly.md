# Stage 06: HybridAnalyzer + `create_analyzer()` (milestone)

- **Status:** todo
- **Priority:** MUST
- **Depends on:** 02, 03, 04, 05

## Goal

Assemble the full pipeline into `HybridAnalyzer`, which implements the contract `Analyzer`, and export it from `create_analyzer()`. **After this stage the backend can switch from the fake to the real AI** (`EDUHUB_FAKE_AI=0`).

## Read first

- `src/shared/eduhub_shared/interfaces.py` (`Analyzer`, `ProgressCallback`)
- `src/shared/eduhub_shared/testing.py` (`check_analyzer`, `assert_report_matches_snapshot`: these define "valid")
- Handoff notes of stages 02–05

## Design

- **`analyzer.py`:** `HybridAnalyzer(settings, client: LLMClient | None, clock: Callable[[], datetime])`, with `async analyze(snapshot, on_progress=None) -> AnalysisReport`. The steps and their progress messages:
  1. **Selection + deterministic features + scores**: 0.10 "Leyendo tus posts".
  2. **Below `MIN_SCORABLE_POSTS`:** raise `AnalysisError("Necesitamos al menos 20 posts con vistas para analizar la cuenta.")`. **Decided:** no reduced report. Better no analysis than a wrong one.
  3. **Labeling**: 0.30 "Clasificando temas y estilo". If it fails or is disabled, continue without labels.
  4. **Stats**: 0.60 "Calculando patrones".
  5. **Pattern model hook**, a no-op placeholder that stage 07 fills in.
  6. **Insight writer**: 0.80 "Escribiendo tus insights". Uses the fallback on failure.
  7. **Assemble the `AnalysisReport`:**
     - `posts` = **every snapshot post, in order** (unscorable ones with `score=None`);
     - explanations on the top and bottom posts;
     - `engine="hybrid-v1"`; and
     - `generated_at=clock()`.
- **Progress values must be non-decreasing.** Log the timing of each step.
- **Error mapping:** labeling and writer failures never raise. Only "not enough data" raises (`AnalysisError`). Unexpected exceptions are wrapped in `AnalysisError("No pudimos analizar la cuenta. Probá de nuevo.")`, with logging.
- **`eduhub_ai/__init__.py`:** `create_analyzer()` builds the settings, then `OpenRouterClient` (or `None` when `AI_ENABLE_LLM=0` or there's no key), then `HybridAnalyzer`. Without a key it still works, in template mode, and logs a warning.

## Tests to write first (`src/ai/tests/test_stage_06_analyzer.py`) → STOP for approval

- `await check_analyzer(HybridAnalyzer(..., client=ScriptedLLMClient(<taxonomy, label batches, texts>)))` passes on the shared fixture snapshot. This is **the contract test**.
- The same with `client=None` (template mode): passes, and `engine == "hybrid-v1"`.
- A labeling failure (scripted exception) → the report is still produced, with topic segments absent and other segments present.
- A writer failure → the template insights are produced.
- 10 scorable posts → `AnalysisError` with an es-AR message.
- Replies, reposts and too-recent posts appear in `report.posts` with `score=None` and are absent from the segments.
- Progress callback values are non-decreasing and end at 0.8 or above.
- `create_analyzer()` with an empty env returns an object satisfying `isinstance(x, Analyzer)` and makes no network call at construction.
- Determinism: the same snapshot, scripted client and clock → an identical report JSON.

## Definition of done

- [ ] Tests green, plus ruff and style
- [ ] Manual end-to-end run (developer has a key): fixture snapshot → real model → read the report together; record the latency and token cost in the handoff notes (target under 60 s, about $0.005)
- [ ] **Merge `ai` into `dev`**, tell Mark that `create_analyzer()` is ready, and confirm the backend runs with `EDUHUB_FAKE_AI=0`
- [ ] Commit `ai: stage 06 hybrid analyzer`

## Handoff notes

_(fill in when done: latency, cost, observations about text quality)_
