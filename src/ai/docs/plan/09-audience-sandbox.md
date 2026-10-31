# Stage 09: Audience sandbox + `create_simulator()`

- **Status:** done (not merged into `dev` yet)
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

- [x] Tests green, plus ruff and style (295 passed: shared + all stages)
- [x] `personas.json` committed with no survey ids; its build script or notebook committed (492 personas, new shuffled ids)
- [x] Cost per simulation (24–50 personas × 2 variants) logged; target under $0.02 (~$0.003–0.004 for 30 × 2)
- [ ] Merge into `dev`, and tell Mark and the front team that the sandbox can be enabled
- [x] Commit `ai: stage 09 audience sandbox`

## Handoff notes

- Built on 2026-10-31: `scripts/build_personas.py` (stdlib csv, run once on `data/raw/base-datos-encc-2022-2023.csv`, downloaded from datos.cultura.gob.ar via its CKAN API), `eduhub_ai/sandbox/data/personas.json` (492 X users, ~4.7M people represented, 188 KB), `sandbox/personas.py` (`load_personas`, `sample_personas`, `personas_available`), `sandbox/prompts.py` (`SANDBOX_SYSTEM`), `sandbox/simulator.py` (`LLMAudienceSimulator`, `ReactionsResponse`, aggregation, `DISCLAIMER`), `scripts/simulate.py` (manual real run with cost).
- Tests: `src/ai/tests/test_stage_09_sandbox.py`, approved by Juan (code was written before approval at the developer's request).
- `create_simulator()` returns `LLMAudienceSimulator` only with the LLM available **and** `personas.json` present; otherwise `None` (the approved stage 06 test, run without a key, still sees `None`). **Heads-up for Mark and the front:** with a key in the backend env, `/features` turns the simulation on and `/simulations` stops returning 501.
- Decisions beyond the plan:
  - **Sampling is simple random (seeded) within the filters, aggregation is weighted by `expansor`.** The plan said "weighted sample" *and* "aggregate with the weights"; doing both counts the weights twice. The contract's "weighted share" is kept in the aggregation.
  - Traits come only from columns with a clear meaning: posting frequency (`int12.1`), daily influencer viewing (`int12.4`), following the news (`noti1`) and news on the phone (`noti4`); platforms from `int11_*`; NSE from `nse_3` mapped to Alto/Medio/Bajo. Other habit columns were left out until someone checks the questionnaire.
  - The LLM sees each persona's profile but not its weight (it should not bias the role-play).
  - Batches of 10 personas × all variants, concurrent, label model + `AI_LABEL_REASONING`, temperature 0.7. A failed batch yields no reactions (no retry, to keep it cheap); unknown persona ids, out-of-range variants and repeats are dropped; fewer than half of the expected reactions → `SimulationError`. Rate limits propagate (429).
  - Segments cover all four `AudienceDimension`s; the summary names the winner, the runner-up and the best age group (≥ 3 personas).
- First real run (2026-10-31, 30 personas × 2 variants): 6.8 s, 3 calls, **$0.0029** (target < $0.02). Comments sound rioplatense and the ranking made sense (free spreadsheet > delivery question), but rates were inflated (77.7% interaction, 14/30 bookmarks, 0 ignores), far above real X engagement. The prompt now anchors on real base rates (most people ignore or just read; bookmark/repost rarer than like; decide each persona separately). Present the sandbox as a **comparison** between variants, never as an engagement forecast. Segments with 1–2 personas swing between 0% and 100%; the summary only cites segments with ≥ 3.
- Second run with the base-rate prompt: 2.8 s, $0.0036; rates still high (41.1% vs 62.1%) but the **ranking held** (variant 2 won both runs, driven by bookmarks). Conclusion: the LLM role-play ranks variants consistently but is not calibrated in absolute terms. **The summary now compares variants** ("La variante 2 generó 1,5 veces más interacción que la variante 1… Donde mejor funcionó fue entre personas de 30 a 49 años.") instead of quoting percentages. `interaction_rate` stays in the result (contract); **front heads-up:** show it as a comparison between variants (bars, ranking), not as a forecast of real engagement.
- Cost per simulation: ~$0.003–0.004 for 30 personas × 2 variants (3 calls, 3–7 s) → ✓ target.
