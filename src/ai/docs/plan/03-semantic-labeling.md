# Stage 03: Semantic labeling (topic, tone, sentiment, hook, CTA)

- **Status:** todo
- **Priority:** MUST
- **Depends on:** 01 (LLM client), 02 (features to fill in)

## Goal

Two LLM passes with a cheap model:
1. **Taxonomy:** propose 5–8 account-specific topics (short Spanish labels) + `otros`.
2. **Labeling:** assign topic, tone, sentiment, hook and CTA to every post, in parallel batches.

The output is validated and merged into each post's `PostFeatures`. **If the LLM fails, analysis continues** with the labels set to `None`.

## Read first

- `../research.md` §4.1, §9 D3, D9, §10 D3
- `01-foundations-llm-client.md` handoff notes (the `LLMClient` API)
- `src/shared/eduhub_shared/models/analysis.py` (`PostFeatures`)

## Label sets (documented in `labeling/schemas.py`; values are es-AR)

| Field | Allowed values |
|---|---|
| tone | `informativo`, `opinión`, `humor`, `personal`, `conversacional`, `promoción`, `inspiracional` |
| hook | `pregunta`, `dato`, `afirmación fuerte`, `historia`, `lista`, `ninguno` |
| cta | `guardar`, `responder`, `compartir`, `seguir`, `link`, `ninguno` |
| sentiment | float in −1..1 |
| topic | one of the account taxonomy labels, or `otros` |

## Design

- **`labeling/schemas.py`:**
  - pydantic response models: `TaxonomyResponse(topics: list[str], 5..8)`, `PostLabel(post_id, topic, tone, sentiment, hook, cta)`, `LabelBatchResponse(labels: list[PostLabel])`;
  - `Literal` types for tone/hook/cta; and
  - the topic enum built **dynamically** from the taxonomy (`create_model`), so the JSON schema restricts topics to the list.
- **`labeling/prompts.py`:** es-AR system prompts with short, explicit rules and 1–2 examples per label. Keep them **stable** (no timestamps) so they can be cached.
- **`labeling/labeler.py`:**
  - `async def build_taxonomy(posts, client, settings) -> list[str]`: takes a sample of up to 60 posts (deterministic: evenly spaced by date). Normalizes labels (lowercase, trimmed, deduplicated), and always appends `otros`.
  - `async def label_posts(posts, taxonomy, client, settings, batch_size=25) -> dict[str, PostLabel]`: runs batches concurrently (the client semaphore limits them).
    - Missing or unknown post ids in a response are ignored.
    - Posts left unlabeled after one retry of their batch get no labels.
  - `def apply_labels(features: dict[str, PostFeatures], labels) -> dict[str, PostFeatures]`: uses `model_copy`.
  - `async def label_account(...) -> LabelingResult` with `features`, `taxonomy`, `coverage` (share labeled) and `errors`. **It never raises for LLM failures.** If the taxonomy fails, fall back to the hashtag-based topic (the fake's approach), or `None`.
- `AI_ENABLE_LLM=0` → skip all calls and return `None` labels.

## Tests to write first (`src/ai/tests/test_stage_03_labeling.py`) → STOP for approval

All tests use `ScriptedLLMClient`, with no network.
- The taxonomy is normalized and deduplicated, includes `otros`, and has at most 9 entries. The sample is deterministic and has at most 60 posts.
- The labeling schema rejects a topic that isn't in the taxonomy (validation error → retry path).
- 60 posts with `batch_size=25` → 3 calls. Every post id gets its label. Labels merge into `PostFeatures` without touching the deterministic fields.
- A batch that fails twice → those posts keep `None` labels, `coverage < 1`, errors are recorded, and nothing raises.
- A taxonomy failure → hashtag fallback topics, and labeling still runs (or is skipped) without raising.
- `AI_ENABLE_LLM=0` → zero LLM calls.
- Sentiment outside −1..1 is rejected by validation.
- The prompts contain no current date or time (cache stability).

## Definition of done

- [ ] Tests green, plus ruff and style
- [ ] The label sets are documented in `labeling/schemas.py` and match this file
- [ ] Optional manual check: label the 40 fixture posts with the real model (the developer runs it) and skim the results
- [ ] Commit `ai: stage 03 semantic labeling`

## Handoff notes

_(fill in when done)_
