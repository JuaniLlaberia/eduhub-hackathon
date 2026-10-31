# AI module: implementation plan

Owner: AI team (Llabe, Tomi), on branch `ai`. Decisions behind this plan: [`../research.md`](../research.md) §9–10.
Every stage is a separate `.md` file, written so a **fresh Claude Code session** can pick it up with no prior context.

## How to run a stage (protocol for every session)

1. **Read in this order:** root `CLAUDE.md` → `src/ai/CLAUDE.md` → this file → the stage file → the files the stage lists under "Read first".
2. **Check the gates:**
   - You are on branch `ai`.
   - `python scripts/check_contracts.py` is clean.
   - The stages listed under "Depends on" are `done` in the status table below.
3. **Write the tests first** (stage section "Tests to write first"), in `src/ai/tests/`. Then **STOP**: show them to the developer and wait until a human approves them with `python scripts/approve_tests.py <files>`. Never edit approved tests.
4. **Implement** until the stage's tests and all earlier tests pass:
   ```bash
   pytest src/shared src/ai && ruff check src/ai && python scripts/check_style.py src/ai
   ```
5. **Close the stage:**
   - Tick the "Definition of done" items.
   - Fill in "Handoff notes" (what was built, deviations, follow-ups).
   - Update the status table below.
   - Commit on `ai` with a message like `ai: stage NN <title>`.
6. **If the plan is wrong or a contract change looks necessary,** stop and ask the developer. Don't improvise contract changes (`CLAUDE.md` §3).

## Stages

| # | Stage | Priority | Depends on | Status |
|---|---|---|---|---|
| 00 | [Contract v1.1.0: hook + CTA](00-contract-hook-cta.md) | MUST | none | done (committed to `main`) |
| 01 | [Foundations: settings + LLM client](01-foundations-llm-client.md) | MUST | none | done |
| 02 | [Deterministic features, post selection, score](02-features-selection-score.md) | MUST | 00 | done |
| 03 | [Semantic labeling (topic, tone, sentiment, hook, CTA)](03-semantic-labeling.md) | MUST | 01, 02 | done |
| 04 | [Stats engine (KPIs, heatmap, segments, significance)](04-stats-engine.md) | MUST | 02 | done |
| 05 | [Insight writer (grounded es-AR texts)](05-insight-writer.md) | MUST | 01, 04 | done |
| 06 | [HybridAnalyzer + `create_analyzer()`: **milestone, hand-off to backend**](06-analyzer-assembly.md) | MUST | 02–05 | done (in `dev`) |
| 07 | [Ridge pattern model (optional per account)](07-ridge-pattern-model.md) | MUST (quality) | 06 | done (in `dev`) |
| 08 | [Draft generator + `create_generator()`](08-draft-generator.md) | WANTED | 06 (07 optional) | done (in `dev`) |
| 09 | [Audience sandbox + `create_simulator()`](09-audience-sandbox.md) | STRETCH | 01 | done (in `dev`) |
| 10 | [Evaluation, bake-off and demo hardening](10-evaluation-demo-hardening.md) | MUST (before demo) | 06 | mostly done (in `dev`; team review and pitch numbers pending) |
| 11 | [Creator brief ("el para qué"), Option A](11-creator-context.md) | WANTED (multi-team; after the demo path works) | 06, 08, 09 + contract v1.2.0 | todo (planned) |

**Critical path to a working demo:** 00 → 01 → 02 → 03 → 04 → 05 → **06**. After 06, the backend can switch `EDUHUB_FAKE_AI=0`.
Stages 01, 02 and 04 are independent enough to run in parallel if the team splits.

## Target module layout (`src/ai/eduhub_ai/`)

```
eduhub_ai/
├── __init__.py            # create_analyzer / create_generator / create_simulator (contract C3)
├── config.py              # AISettings from env vars
├── llm/                   # stage 01
│   ├── client.py          # LLMClient protocol + LLMError
│   ├── openrouter.py      # OpenRouterClient (OpenAI-compatible SDK)
│   └── scripted.py        # ScriptedLLMClient for tests (no network)
├── features/              # stage 02
│   ├── selection.py       # which posts are scorable
│   ├── deterministic.py   # P1 features
│   └── scoring.py         # score (c)
├── labeling/              # stage 03
│   ├── schemas.py         # label enums + JSON schemas
│   ├── prompts.py
│   └── labeler.py         # taxonomy pass + batch labeling
├── stats/                 # stage 04
│   ├── kpis.py
│   ├── timing.py          # heatmap, hour blocks, best slots
│   ├── segments.py        # segment stats + bootstrap CI
│   └── significance.py
├── insights/              # stage 05
│   ├── evidence.py        # compact evidence JSON for the LLM
│   ├── writer.py          # LLM call → insights/recs/explanations/summary
│   ├── grounding.py       # every number in text must exist in evidence
│   └── fallback.py        # template texts (reuses eduhub_shared.fakes builders)
├── analyzer.py            # stage 06: HybridAnalyzer
├── patterns/              # stage 07
│   ├── base.py            # PatternModel protocol
│   ├── ridge.py
│   └── evaluation.py      # pairwise accuracy
├── generation/            # stage 08
└── sandbox/               # stage 09 (+ data/personas.json)
```

Notebooks go in `src/ai/notebooks/` (Colab), and tests in `src/ai/tests/` (one file per stage: `test_stage_NN_<name>.py`).
Sessions may adjust the inner layout if the developer agrees. The **public surface is fixed**: the three factories in `eduhub_ai/__init__.py`.

## Global rules for every stage

- **Contract first.** Inputs are `eduhub_shared.models` objects, and outputs must pass `eduhub_shared.testing.check_*`. Rates come only from `eduhub_shared.metrics`. Never edit `src/shared/` outside stage 00.
- **No network in tests.** LLM calls go through `ScriptedLLMClient`, and randomness gets a fixed seed.
- **Numbers are computed, never generated.** The LLM labels and writes. Every number in user-facing text comes from computed evidence.
- **es-AR** for everything a user sees (voseo, concrete, short). English for code and docs.
- **Degrade, don't crash.** If the LLM fails, use template texts, and keep the computed numbers. Raise `eduhub_shared.errors` exceptions only when no report is possible.
- **Python style:**
  - Type hints and the docstring format `"""` / text / `"""` on every function and class, with no blank line after the docstring.
  - Exactly one blank line between definitions. Never run `black` or `ruff format`.
- **Dependencies** go in `src/ai/pyproject.toml` only. Keep the runtime light: no torch.

## Environment variables (AI)

| Var | Default | Use |
|---|---|---|
| `OPENROUTER_API_KEY` | none (required for real calls) | Auth |
| `AI_LABEL_MODEL` | `deepseek/deepseek-v4.1-flash` | Labeling, sandbox |
| `AI_WRITER_MODEL` | `deepseek/deepseek-v4.1-flash` | Insights, drafts |
| `AI_FALLBACK_MODELS` | empty (comma-separated slugs, e.g. a Claude Haiku-class model) | OpenRouter fallback list |
| `AI_LLM_TIMEOUT_S` | `30` | Per-call timeout |
| `AI_MAX_CONCURRENCY` | `8` | Parallel labeling batches |
| `AI_ENABLE_LLM` | `1` | `0` = template-only mode (no LLM calls) |

Verify the model slugs on openrouter.ai before the first real call (`../research.md` §5.4).
