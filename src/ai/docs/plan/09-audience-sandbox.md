# Stage 09: Audience sandbox + `create_simulator()`

- **Status:** todo
- **Priority:** STRETCH (nothing may depend on it)
- **Depends on:** 01

## Goal

Test 1–3 text variants against a **synthetic Argentine audience** whose personas are sampled from **real ENCC 2022-23 respondents who use X** (OpenARG). Each persona "reacts" (ignore/read/like/reply/repost/bookmark) via a cheap LLM, and results are aggregated with the survey weights, by variant and by segment. **Always show the disclaimer: it compares variants, it doesn't predict real engagement.**

## Read first

- `docs/validation.md` §1.1 and §1.3 (ENCC, the 492 X users, the weights)
- `scripts/validation/encc_analysis.py` (column meanings: `int11_6` = uses Twitter, `expansor`, `grupos_edad`, `genero`, `provincia`, `nse_3`)
- `src/shared/eduhub_shared/models/simulation.py` and `testing.check_simulator`
- `src/shared/eduhub_shared/fakes.py` (`FakeAudienceSimulator`: the aggregation logic to port)

## Design

- **Offline data prep (notebook or script, run once):** `src/ai/notebooks/build_personas.ipynb` or `src/ai/scripts/build_personas.py`:
  - Download the ENCC CSV (the URL is in `docs/validation.md`) into `data/raw/`, which is git-ignored.
  - Filter the X users and build `Persona` objects: age group, gender, province, NSE, platforms used, and 3–5 es-AR traits derived from consumption answers (e.g. watches influencers daily, posts weekly, reads news online).
  - Write `eduhub_ai/sandbox/data/personas.json`. That's anonymous open data, so it's fine to commit, but **no ids from the survey**: use new ids.
- **`sandbox/personas.py`:** `load_personas()` + `sample_personas(filters, n, seed) -> list[Persona]`, a weighted sample by `expansor` (the `weight` field).
- **`sandbox/simulator.py`:** `LLMAudienceSimulator(settings, client, clock)`:
  - batches of about 10 personas × all variants per call (cheap model);
  - the response schema has `reactions[]` with `persona_id`, `variant_index`, `reaction`, an optional short es-AR `comment`, and `sentiment`;
  - aggregation ported from the fake: weighted `interaction_rate` per variant and per `AudienceDimension` segment, `best_variant_index`, an es-AR `summary`, and the constant disclaimer.

  Missing reactions are dropped. If more than half are missing → `SimulationError`.
- **`create_simulator()`:** return `None` (feature disabled) unless `personas.json` exists **and** an LLM client is available.

## Tests to write first (`src/ai/tests/test_stage_09_sandbox.py`) → STOP for approval

- `load_personas()` gives valid `Persona` objects with weights > 0. The weighted sample is deterministic with a seed and respects filters (age group, gender, province).
- `await check_simulator(LLMAudienceSimulator(... ScriptedLLMClient ...))` passes (contract test).
- Aggregation: on a scripted set where variant 1 gets more active reactions from heavily weighted personas, variant 1 wins. Segment rates are computed per dimension value.
- More than half the reactions missing → `SimulationError`.
- `create_simulator()` returns `None` without a key or without `personas.json`.

## Definition of done

- [ ] Tests green, plus ruff and style
- [ ] `personas.json` committed with no survey ids; its build script or notebook committed
- [ ] Cost per simulation (24–50 personas × 2 variants) logged; target under $0.02
- [ ] Merge into `dev`, and tell Mark and the front team that the sandbox can be enabled
- [ ] Commit `ai: stage 09 audience sandbox`

## Handoff notes

_(fill in when done)_
