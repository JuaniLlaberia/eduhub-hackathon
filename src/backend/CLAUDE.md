# src/backend: Back team (Mark)

Scope, open questions and suggested tools: `docs/teams/backend.md`. Flows and API: `docs/architecture.md` §6–7.

You implement:
- **`PostSource` adapters**, including a `FixturePostSource` (`eduhub_shared.fakes.FakePostSource` already replays the fixture).
- **`PostPublisher`.**
- **The analysis job runner** (queued → fetching → analyzing → done or failed, with progress).
- **Storage.**
- **Every route in `src/shared/contracts/openapi.json`**, using the `eduhub_shared.models` classes as request and response models.
- **Feature flags and `DEMO_MODE`.**
- **Deployment.**

Contract obligations:
- Every error body is `ErrorResponse`. That includes FastAPI validation errors (422): override the `RequestValidationError` handler. Map `eduhub_shared.errors` exceptions with their `.code`.
- Disabled features answer 501 with `feature_disabled`, and `/features` reports them as false.
- Get the AI only through `from eduhub_ai import create_analyzer, create_generator, create_simulator`. With `EDUHUB_FAKE_AI=1`, use `eduhub_shared.fakes.FakeAnalyzer` and the other fakes instead. `create_simulator()` returning `None` means the simulation feature is disabled.
- The contract tests you must write (TDD, approved by Mark):
  - `eduhub_shared.testing.assert_routes_match_contract(fastapi_routes(app))`
  - `await check_post_source(source, handle)` for each source
  - API tests that validate responses against the shared models
- Never put analysis logic here. Anything that interprets posts belongs to the AI team.
- Keep your dependencies in `src/backend/pyproject.toml`, and tests in `src/backend/tests/`.
