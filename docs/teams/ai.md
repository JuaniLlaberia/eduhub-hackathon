# AI team (Llabe, Tomi)

Owns `src/ai/` (the `eduhub_ai` package): features, analysis, insights, recommendations, draft generation and the audience sandbox.
Implements the **C3** interfaces. The input is always an `AccountSnapshot`. **Never fetch X data yourselves.**

> Research and decisions (approach, methods, models, costs): [`src/ai/docs/research.md`](../../src/ai/docs/research.md).

## What `eduhub_ai` must export (contract C3)

```python
from eduhub_ai import create_analyzer, create_generator, create_simulator
analyzer = create_analyzer()          # -> Analyzer           (MUST)
generator = create_generator()        # -> DraftGenerator     (WANTED)
simulator = create_simulator()        # -> AudienceSimulator | None   (STRETCH; None = disabled)
```

Configuration comes from environment variables that you read yourselves (e.g. `OPENROUTER_API_KEY`, model names).

## First decision: hybrid ML + LLM, or LLM agents only?

| | A. LLM / agents only | **B. Hybrid (suggested)** |
|---|---|---|
| Numeric features (length, hour, media…) | LLM reads the posts | Deterministic Python (pandas) |
| Semantic features (topic, tone, sentiment) | LLM | LLM in batches with **structured output** (or embeddings + clustering for topics) |
| Stats (best hours, segments, KPIs) | LLM summarizes; numbers can be **wrong or invented** | pandas group-bys and medians: **exact** |
| "Why it worked" | LLM opinion | Simple interpretable model (e.g. regression or gradient boosting on log engagement + feature importance) **+ an LLM that writes insights only from the computed evidence** |
| Speed and cost | Many long prompts | Few short prompts |
| Pitch for "uso de IA" | "We use an LLM" | "ML finds the patterns; the LLM explains them and writes in your voice" |

Why B: the jury will ask whether the numbers are real. LLMs are bad at arithmetic over 200 posts. In B, every number on the dashboard is computed, and the LLM only writes text grounded on that evidence.

## Suggested pipeline (option B)

1. `features`: deterministic features plus LLM labels (topic from a fixed or account-specific taxonomy, tone, sentiment) → `PostFeatures`.
2. `metrics`: rates come from `eduhub_shared.metrics` (C5; don't re-implement them). **Score** = post engagement relative to the account median. Define the exact formula and document it.
3. `stats`: KPIs, heatmap (weekday × hour, Argentina time), segment stats, best time slots.
4. `drivers`: feature importance / contrasts (top vs bottom posts).
5. `insights` + `recommendations` + `summary`: LLM with the evidence as input → es-AR text, each insight with `evidence[]` and `related_post_ids[]`.
6. `generation` (WANTED): few-shot with the creator's top posts + insights + current trends → drafts in their voice + suggested time + `estimated_score`.
7. `sandbox` (STRETCH): personas sampled from **ENCC 2022-23 X users** (492 respondents, weighted by `expansor`; see `docs/validation.md` §1.3 and `scripts/validation/encc_analysis.py`) → LLM role-play per persona → reactions by segment. Present it as "compare variants", never as "prediction".

## Suggested tools (your call)

pandas · scikit-learn · pydantic (structured output parsing) · OpenRouter (OpenAI-compatible API; e.g. a fast, cheap model for labeling and a stronger one for insights and generation, such as Claude Haiku/Sonnet; check the exact model IDs on OpenRouter) · Google Colab Pro for any training or notebook work · optional: `pysentimiento` (Spanish sentiment trained on tweets, built by Argentine researchers; pulls in torch, which is heavy to deploy) · pytest with fixture snapshots + mocked LLM calls.

## Open questions (decide and write your answers here)

- [ ] Option A or B? (first task once the split is done)
- [ ] Exact **score** definition and **topic taxonomy** (fixed list or per account?).
- [ ] Minimum data: what happens with fewer than ~30 posts, or with posts missing `impressions` (X only shows views for posts after late 2022)?
- [ ] Latency and cost budget per analysis (target: under 60 seconds and a few cents).
- [ ] Evaluation: for example, does the model rank held-out pairs of posts better than chance? (This is a good pitch point.)
- [ ] Which models (cheap vs strong), and the fallback if OpenRouter fails during the demo.
- [ ] Sandbox: how many personas, which LLM, what each reaction looks like, and how to aggregate them.
