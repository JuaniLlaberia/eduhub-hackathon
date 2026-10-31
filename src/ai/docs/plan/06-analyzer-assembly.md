# Stage 06: HybridAnalyzer + `create_analyzer()` (milestone)

- **Status:** done (not merged into `dev` yet; real-model run pending)
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

### Backend integration notes (from the back team, 2026-10-31, contract v1.1.0)

- With `EDUHUB_FAKE_AI=0`, the backend calls **all three** factories at startup, and any exception (including `NotImplementedError`) stops the server. So when this stage ships, `create_generator()` must **not raise** either: until stage 08, return a working stand-in (e.g. `eduhub_shared.fakes.FakeDraftGenerator`).
- **Tell the back team before merging this stage into `dev`.** They have a test that currently expects the `NotImplementedError`, and they'll change it at the same time.
- `create_simulator()` returning `None` disables the sandbox (`/features` → false, `/simulations` → 501). That's fine until stage 09.
- **`report.id` is the backend's `report_id`.** It must be unique on every run. `handle + timestamp` (as in the fake) is fine.
- `on_progress(value, message)`: the backend maps 0–1 to the job's 0.10–0.99 range and shows `message` (es-AR) as the job message.
- Errors: the `message` of `AnalysisError` / `GenerationError` / `SimulationError` reaches the user (es-AR). `RateLimitedError` → 429. Any other exception → generic 500, with the text hidden. So wrap unexpected failures, as described above.
- `generate()` (stage 08) receives the account's latest report plus current Argentine trends (from twitterapi.io).

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

- [x] Tests green, plus ruff and style (227 passed: shared + stages 01–06)
- [ ] Manual end-to-end run (developer has a key): fixture snapshot → real model → read the report together; record the latency and token cost in the handoff notes (target under 60 s, about $0.005)
- [ ] **Merge `ai` into `dev`**, tell Mark that `create_analyzer()` is ready, and confirm the backend runs with `EDUHUB_FAKE_AI=0`
- [x] Commit `ai: stage 06 hybrid analyzer`

## Handoff notes

- Built on 2026-10-31: `eduhub_ai/analyzer.py` (`HybridAnalyzer`, `ENGINE = "hybrid-v1"`, `Progress`), `eduhub_ai/__init__.py` (`create_analyzer` → `HybridAnalyzer` with `OpenRouterClient` or template mode; `create_generator` → `FakeDraftGenerator` until stage 08; `create_simulator` → `None`).
- Tests: `src/ai/tests/test_stage_06_analyzer.py` (incl. `check_analyzer` with a scripted LLM and in template mode, `check_generator`, real snapshots locally). Approved by Juan (code was written before approval at the developer's request).
- Pipeline: select (now = `snapshot.collected_at`) → features + scores → label **scorable posts only** (replies keep `None` labels) → stats → evidence → writer → report. Progress: 0.10 "Leyendo tus posts", 0.30 "Clasificando temas y estilo", 0.60 "Calculando patrones", 0.80 "Escribiendo tus insights", 1.0 "Análisis listo". Each step's duration is logged.
- Report id: `uuid5(namespace, "hybrid-v1|handle|generated_at")`, unique per run with the real clock, identical for identical input and clock.
- Decisions beyond the plan:
  - When there is no LLM taxonomy (template mode or taxonomy failure), topics fall back to the first hashtag (`hashtag_topics`). So the plan's "labeling failure → topic segments absent" became "tone/hook/CTA segments absent, topic from hashtags" (the fixture keeps its "presupuesto" story in template mode).
  - The pattern-model step is `_pattern_effects()` returning `[]`; stage 07 fills `EvidencePack.pattern_effects` there.
  - Only `ContractError`s pass through; anything else becomes `AnalysisError("No pudimos analizar la cuenta. Probá de nuevo.")` with the traceback logged.
- **Integration gotcha (back team):** the backend reads `.env` with pydantic-settings, which does **not** export values to `os.environ`, while `load_settings()` reads `os.environ`. Start the backend with the env exported (e.g. `uvicorn ... --env-file .env`, or `set -a; source .env; set +a`), or the analyzer silently runs in template mode (it logs a warning).
- **Real-model runs (2026-10-31, `deepseek/deepseek-v4.1-flash` via OpenRouter):**

  | Run | Settings | Time | Notes |
  |---|---|---|---|
  | bilinkis, 40 posts, labels only | default reasoning, cheapest providers | 45.5 s | ~20 s per call (reasoning tokens, `fp4` providers) |
  | paulina_cocina, full pipeline to the writer | same | 101.4 s | texts excellent, all grounded |
  | bilinkis, 40 posts, labels only | `AI_LABEL_REASONING=off`, `AI_PROVIDER_SORT=throughput` | 4.6 s | 1–3 s per call (Wafer, Together); topics slightly vaguer |
  | paulina_cocina, full pipeline to the writer | + `AI_WRITER_REASONING=low` | 27.0 s | 7 label batches in ~4 s; writer 21.8 s / 3.5k output tokens; ~33k in + 16k out ≈ $0.02 |

  Quality notes: the writer's texts are concrete, voseo, grounded (0 rejected numbers). The labeler over-used `cta = link` for trailing `t.co` media links, which led to a false "sacá el link" recommendation; the label prompt now says a trailing `t.co` link is the attached media. Explanations repeated multipliers; the writer prompt now allows at most one number per explanation. Numbers written as words ("los cinco bottom posts") are not checked by grounding.
- Still open: the merge into `dev` coordinated with Mark (their `test_real_ai_fails_until_eduhub_ai_is_delivered` must change at the same time).
