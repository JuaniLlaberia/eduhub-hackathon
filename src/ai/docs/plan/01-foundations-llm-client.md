# Stage 01: Foundations (settings + LLM client)

- **Status:** todo
- **Priority:** MUST
- **Depends on:** none

## Goal

A small, swappable LLM layer: one `complete_json` call that returns a **validated pydantic object**, via OpenRouter, with timeout, retry on invalid JSON, a fallback model list, and a scripted fake for tests. Plus the settings object for every AI env var.

## Read first

- `README.md` (this folder), especially the env var table
- `../research.md` §5.2, §5.4 (OpenRouter structured outputs need `require_parameters: true`; support varies per endpoint)
- `src/shared/eduhub_shared/errors.py`

## Design

- **Dependencies** (`src/ai/pyproject.toml`): `openai>=1.x`, used as the OpenAI-compatible SDK with `base_url="https://openrouter.ai/api/v1"`. Check that the Python 3.14 wheels install.
- **`eduhub_ai/config.py`:** `AISettings` frozen dataclass plus `load_settings(env: Mapping[str, str] | None = None) -> AISettings`, covering every var in README's table. Parse types, apply defaults, and **don't read `.env` files** (the backend or shell provides the env).
- **`eduhub_ai/llm/client.py`:**
  - `class LLMClient(Protocol)` with `async def complete_json(self, *, model: str, system: str, user: str, schema: type[T], temperature: float | None = None) -> T`
  - `class LLMError(Exception)` with a `retryable: bool` attribute
- **`eduhub_ai/llm/openrouter.py`:** `OpenRouterClient(settings)`:
  - Send `response_format={"type": "json_schema", "json_schema": {"name": schema.__name__, "strict": True, "schema": schema.model_json_schema()}}`.
  - Send `extra_body={"provider": {"require_parameters": True}, "models": [model, *settings.fallback_models]}` when fallbacks are configured.
  - Parse with `schema.model_validate_json`. On a validation error, retry **once**, appending the validation error to the user message.
  - Timeout = `settings.llm_timeout_s`.
  - Map 429 → `eduhub_shared.errors.RateLimitedError`, other failures → `LLMError`.
  - Log the model used, tokens and latency (use `logging`, not `print`).
  - A semaphore with `settings.max_concurrency` limits parallel calls.
- **`eduhub_ai/llm/scripted.py`:** `ScriptedLLMClient(responses: list[str | Exception | Callable])`. It returns or raises the queued items in order, records every call (model, system, user, schema) for assertions, and validates the output with the same parsing code path.
- **A shared parsing helper** (`parse_or_raise(text, schema)`), used by both clients, so the retry logic is testable without network.

## Tests to write first (`src/ai/tests/test_stage_01_foundations.py`) → STOP for approval

- `load_settings({})` gives the documented defaults. Custom values parse correctly (ints, comma-separated fallback list, `AI_ENABLE_LLM=0`). Invalid ints raise `ValueError`.
- `ScriptedLLMClient` returns a validated pydantic object from a JSON string and records the call.
- Invalid JSON then valid JSON → one retry, success. The second call's user message includes the validation error.
- Invalid twice → raises `LLMError`.
- A queued `RateLimitedError` propagates unchanged.
- `OpenRouterClient` builds the request correctly (model, `response_format` with strict schema, `require_parameters`, fallback `models` list). Test this by injecting a fake `AsyncOpenAI`-like object (no network).
- The concurrency limit holds: with `max_concurrency=2`, no more than 2 calls are in flight at once.

## Definition of done

- [ ] All tests green, plus ruff and style
- [ ] `AI_*` vars added to the root `.env.example` (repo-wide file: confirm with the developer)
- [ ] Optional manual smoke test (not in CI): a tiny script `src/ai/scripts/smoke_llm.py` that makes one real call with a 2-field schema, printing the model, latency and validated output. Run it only when the developer provides `OPENROUTER_API_KEY`.
- [ ] Commit `ai: stage 01 foundations`

## Handoff notes

_(fill in when done)_
