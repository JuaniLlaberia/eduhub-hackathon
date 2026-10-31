# src/ai: AI team (Llabe, Tomi)

Scope, the hybrid-vs-agents decision, suggested pipeline and open questions: `docs/teams/ai.md`.

Contract obligations:
- `eduhub_ai/__init__.py` exports:
  - `create_analyzer() -> Analyzer`
  - `create_generator() -> DraftGenerator`
  - `create_simulator() -> AudienceSimulator | None`
  
  These are the only things the backend imports. Keep their signatures.
- Input is always an `AccountSnapshot`. **Never fetch X data**, and never branch on `snapshot.source`.
- Rates come from `eduhub_shared.metrics` (do not re-implement). `report.posts` must contain every snapshot post exactly once, in the same order (newest first).
- All user-facing text (insights, recommendations, summary, explanations, drafts) is in Spanish (es-AR). Every number shown in an insight must come from computed data, never from LLM arithmetic.
- Raise `eduhub_shared.errors` exceptions (`AnalysisError`, `GenerationError`, `SimulationError`, `RateLimitedError`) with an es-AR message that's safe to show users.
- The contract tests you must write (TDD, approved by Llabe or Tomi):
  - `await check_analyzer(create_analyzer())`
  - `await check_generator(create_generator())`
  - `await check_simulator(...)` once the sandbox exists
- `eduhub_shared.fakes.FakeAnalyzer` is the baseline to beat, and the demo fallback.
- Mock LLM calls in unit tests (no network in CI). Read keys from env vars (`OPENROUTER_API_KEY`, ...).
- Keep runtime dependencies light (deployment), and put notebooks in `src/ai/notebooks/`. Keep your dependencies in `src/ai/pyproject.toml`, and tests in `src/ai/tests/`.
