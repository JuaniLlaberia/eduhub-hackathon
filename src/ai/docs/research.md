# AI research: approach, methods and models

> Owner: AI team (Llabe, Tomi). Status: **decisions agreed 2026-10-30 (§9)**. Implementation plan: [`plan/README.md`](plan/README.md).
> Contract we must satisfy: `Analyzer` / `DraftGenerator` / `AudienceSimulator` in `src/shared/eduhub_shared/interfaces.py`, output models in `src/shared/eduhub_shared/models/`.

## 1. Constraints that shape every choice

| Constraint | Consequence |
|---|---|
| ~8 h of coding, 2 people | Few moving parts. No model training that needs a GPU at runtime. |
| ~40–200 posts per account | **Small data.** Deep models are out; simple, robust statistics and small interpretable models are in. |
| Jury: "uso de tecnología/IA" (20%) + "innovación" (20%) | It must visibly be AI, but the numbers must survive "¿esto es real?" |
| Dashboard numbers must be true | No number comes from LLM arithmetic. LLMs label and write; code computes. |
| Analysis latency | Target **under 60 s** per account (the front polls a job). |
| Cost | Target **a few cents per analysis** (the business model sells credits). |
| Deployment (Mark) | Keep the runtime light: **no torch** in production if we can avoid it. |
| Language | Input is rioplatense Spanish. All output text is es-AR. |
| Demo safety | If the LLM fails, degrade to `FakeAnalyzer`-style templates with the same stats. |

## 2. What "analysis" must produce, broken into sub-problems

`AnalysisReport` (contract) = features + rates + score per post → KPIs, heatmap, segments, best slots → insights, recommendations, explanations, summary.

| # | Sub-problem | Nature | Candidates |
|---|---|---|---|
| P1 | Deterministic features (length, hour, weekday, media, links, hashtags, question, emoji…) | Pure code | pandas (already in `FakeAnalyzer`) |
| P2 | Semantic features (**topic**, **tone**, sentiment, hook type, call to action) | NLP | LLM labeling · embeddings + clustering · pysentimiento |
| P3 | **Performance score** (the target variable) | Definition | See §4.2 |
| P4 | Pattern finding: *what* drives performance for this creator | Statistics/ML | Segment stats · tests · interpretable model |
| P5 | Insights, recommendations, per-post explanations, summary in es-AR | Text generation | LLM grounded on P4 evidence |
| P6 | Drafts in the creator's voice + suggested time + estimated score (WANTED) | Generation (+ scoring) | LLM few-shot + P4 model to score |
| P7 | Synthetic audience sandbox (STRETCH) | Simulation | LLM role-play of ENCC-sampled personas |

## 3. The main decision: LLM-only/agents vs hybrid ML + LLM

| Criterion | A. LLM only / agents | **B. Hybrid: ML/stats compute, LLM labels + explains** | C. Classic ML/NLP only |
|---|---|---|---|
| P1 features | LLM reads posts (waste) | Code | Code |
| P2 topic/tone | LLM | **LLM labeling** (cheap model, structured output) | Embeddings + clustering, pysentimiento |
| P4 patterns | LLM "looks" at the posts: **numbers can be wrong or made up** | **Exact stats + small model with feature importance** | Same as B |
| P5 texts | LLM | **LLM writes only from computed evidence** | Templates (robotic) |
| Correctness for the jury | Weak ("the AI said so") | **Strong** ("computed from your 200 posts, explained by AI") | Strong |
| "Uso de IA" story | Strong but generic | **Strongest:** "ML finds the patterns, AI explains them and writes in your voice" | Weak (no generative AI) |
| Effort for 8 h | Low to start, high to make reliable | Medium (stats are partly written already in `fakes.py`) | Medium-high (topic models need tuning) |
| Cost and latency | High (long prompts with all posts) | Low (short prompts, one cheap labeling pass) | Lowest |
| Testability | Hard (non-deterministic) | Good: stats unit-tested, LLM calls mocked | Good |

**Recommendation: B.** It's the only option that is both credible ("every number is real") and clearly AI-powered.

**About "agentic":** a tempting variant **B+** gives the insight step tools (`get_segment_stats(dimension)`, `compare(a, b)`, `get_posts(filter)`) and lets an LLM agent explore before writing insights. It makes a great pitch line ("un analista de IA que explora tus datos"). But it adds latency (several turns, 30–90 s), non-determinism and test effort. **Suggestion:** build B first, and add B+ only if we have time left. The contract doesn't change either way.

## 4. Method choices per sub-problem (option B)

### 4.1 P2: topic, tone, sentiment

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| **LLM labeling, two passes**: (1) propose a 5–8 topic taxonomy for this account from a sample, (2) assign topic, tone, sentiment, hook and CTA to every post in batches of ~25 with a JSON schema | Works on 40 posts, per-account topics, readable labels in Spanish, one cheap model, no torch | Small cost; some label noise | **Recommended** |
| Embeddings + KMeans/HDBSCAN + LLM names the clusters | More "ML" | Clusters are noisy on 40–200 short texts; extra API or a local model | Fallback or experiment |
| BERTopic | Strong on large short-text corpora | Needs many docs, depends on torch/UMAP, heavy to deploy | Not for runtime |
| pysentimiento (RoBERTuito, trained on Spanish tweets) | Free, local, made for tweets (sentiment macro-F1 ≈ 0.70) | Pulls in torch (heavy deploy); English-coded labels; tone not covered | Optional: **validate the LLM labels in Colab** |

Fixed tone labels (proposal): `informativo`, `opinión`, `humor`, `personal/storytelling`, `pregunta/conversación`, `promoción`, `inspiracional`. Topics are per account (the taxonomy from pass 1).

### 4.2 P3: the performance score (decide together)

The problem: impressions and engagement rate (ER) measure different things. A viral post has high reach but a diluted ER. A post seen only by core fans has a high ER but low reach.

| Option | Formula | Note |
|---|---|---|
| a. ER relative (current fake) | ER_post / median ER | Ignores reach |
| b. Reach relative | impressions_post / median impressions | Ignores quality |
| **c. Combined (proposal)** | geometric mean of (a) and (b) | Rewards both; 1.0 = typical post |
| d. Weighted engagement | (likes + 2·replies + 2·reposts + 3·bookmarks) / median | Matches "saves and shares matter more" from the metrics research; the weights are our choice, not X's (X's weights are redacted) |

Mandatory hygiene, whatever we choose:
- **Exclude posts younger than ~48 h** from scoring. They haven't finished accumulating views.
- Posts without impressions (pre-2023) get `score = None`.
- Analyze **originals + quotes**. Replies and reposts behave differently: show them, but keep them out of the patterns.
- Use medians and logs, never means, because one viral post would distort everything.

### 4.3 P4: pattern finding with small data

1. **Segment stats** by topic, format, length, tone, hour block and weekday: median score, n, and a **bootstrap confidence interval**. Show a segment only if n ≥ 3 (most of this is in `fakes.py` already).
2. **Significance filter:** Mann-Whitney U test (top vs rest) or a check that the CI excludes 1.0. That sets `Insight.confidence` and prevents "insights" based on 2 posts.
3. **Small interpretable model:** ridge regression on log(score) with one-hot features, or scikit-learn `HistGradientBoostingRegressor` + **permutation importance**. It answers *which features matter most once the others are controlled for*. For example, "it's not the hour, it's that you post 'presupuesto' at night", which corrects confounding between topic and time.
4. **Evaluation (pitch point):** cross-validated **pairwise accuracy**: given two held-out posts, does the model rank the better one first? If it reaches more than 50% (say 65–70%), we can say "nuestro modelo acierta X de cada 10 comparaciones". Independent benchmarks show LLMs alone are often close to chance at this, which makes the hybrid look good.
5. **Heatmap / best times:** with 200 posts, weekday × hour cells are sparse. Group hours into blocks (morning/midday/afternoon/night) for insights, and keep the raw heatmap for the chart.

### 4.4 P5: insights, recommendations, explanations, summary

- One call to a strong model. Input: compact JSON with KPIs, the significant segments, model importances, and the top/bottom 5 posts (text + features + score). Output: a JSON schema with `Insight[]`, `Recommendation[]`, explanations for the top/bottom posts, and the summary.
- Prompt rules:
  - es-AR, voseo, concrete.
  - **Every number must be copied from the evidence.**
  - Each insight cites `evidence[]` and `related_post_ids[]`.
- **Guardrail in code:** after the call, check that every number in the text appears in the evidence. If one doesn't, drop the insight or retry. The contract check (`check_analyzer`) already verifies ids.

### 4.5 P6: generation (WANTED)

- A strong model, few-shot with the creator's **top 5–8 posts** (for voice), the insights, the requested topic or recommendation, and the current trends. It produces `count` drafts plus a rationale.
- **Closed loop (innovation point):** score each draft with the P4 model (features from P1 + P2 labels) to fill `estimated_score`, and suggest the best slot from the heatmap. The pitch line: "lo genera la IA y lo evalúa tu propio modelo".

### 4.6 P7: sandbox (STRETCH)

- Personas are sampled, weighted by `expansor`, from the **492 ENCC 2022-23 respondents who use X** (age, gender, province, socioeconomic level, platforms, consumption habits). See `docs/validation.md` §1.3. We pre-compute a `personas.json` offline in Colab, so the runtime needs no CSV.
- To keep the cost low, use one cheap-model call per batch of ~10 personas × variants. The output is a JSON list of reactions. Aggregate with the weights.
- Always show the disclaimer: it compares variants and doesn't predict.

## 5. Models and provider

### 5.1 Candidates (Anthropic list prices per 1M tokens, Oct 2026)

| Role | Model | Input | Output | Why |
|---|---|---|---|---|
| Labeling (P2), sandbox (P7) | **Claude Haiku 5.5** (`claude-haiku-5-5`) | $0.10 | $0.50 | Very cheap and fast, good at structured extraction in Spanish |
| Insights (P5), generation (P6) | **Claude Sonnet 5.5** (`claude-sonnet-5-5`) | $2.00 | $10.00 | Strong writing and voice imitation, at half the price of Opus |
| Quality ceiling (if needed) | Claude Opus 5.5 (`claude-opus-5-5`) | $4.00 | $20.00 | Best quality; probably unnecessary for these tasks |

Prices for prompts up to 100K tokens (Haiku 5.5 costs more beyond that; we'll never get close).

### 5.2 Provider: OpenRouter (we have credits) vs the Anthropic API directly

| | OpenRouter | Anthropic API (official `anthropic` SDK) |
|---|---|---|
| Credits | **Already funded** | New account/credits needed |
| Structured output | `response_format: json_schema` + `strict`. Support varies **per endpoint**, so set `require_parameters: true` in provider routing | Native `output_config.format` / `client.messages.parse()` |
| Prompt caching | `cache_control` is passed through for Claude (5 min, or 1 h TTL; reads at 0.1x) | Native |
| Batch API (50% off) | No | Yes (not useful anyway: we need answers in seconds) |
| Fallback if a provider is down | Can route to another model/provider | Server-side refusal fallbacks only |
| SDK | OpenAI-compatible (`openai` SDK with `base_url`, or `httpx`) | `anthropic` |

**Suggestion:** use **OpenRouter**, since it's already paid for and has provider fallback, behind a tiny internal `LLMClient` interface with methods like `complete_json(schema, messages, model)`. Then switching to the direct Anthropic SDK later is a one-file change. Model slugs on OpenRouter look like `anthropic/claude-…`, but **verify the exact slugs and per-endpoint `structured_outputs` support on openrouter.ai/models** before coding.

### 5.3 Cost and latency estimate per analysis (200 posts)

| Step | Model | Tokens (in / out) | Cost | Time |
|---|---|---|---|---|
| P2 taxonomy pass | Haiku 5.5 | ~6k / ~0.5k | ~$0.001 | ~3 s |
| P2 labeling, 8 batches of 25 in parallel | Haiku 5.5 | ~20k / ~10k | ~$0.007 | ~5–10 s |
| P4 stats + model | (CPU) | n/a | $0 | under 1 s |
| P5 insights | Sonnet 5.5 | ~8k / ~3k | ~$0.046 | ~15–25 s |
| **Total** | | | **≈ $0.05** | **≈ 25–40 s** |

Plus generation ≈ $0.02 per 3 drafts, and the sandbox ≈ $0.01–0.02 per run (Haiku). Prompt caching on the fixed system prompts cuts the input cost further.

### 5.4 Cheaper option requested by the team: DeepSeek V4.1 Flash

| Model (OpenRouter slug) | $/1M in | $/1M out | Notes |
|---|---|---|---|
| **`deepseek/deepseek-v4.1-flash`** | ~$0.02 | ~$0.19 | Successor of V4 Flash. `response_format`, tools and a reasoning toggle are accepted. Prices from OpenRouter listings (Oct 2026); **verify on the live page** |
| `deepseek/deepseek-v4-flash-0731` | ~$0.03 | ~$0.30 | Previous GA snapshot |
| Claude Haiku 5.5 (fallback candidate) | $0.10 | $0.50 | Same price range, very reliable structured output |

- **Cost per analysis with one cheap model for every role:** about **$0.005**, roughly 10x cheaper than the Haiku + Sonnet mix (§5.3), because the Sonnet insight step was most of the cost.
- **Reliability caveats:**
  - Structured-output support depends on the OpenRouter **endpoint** (several providers serve DeepSeek), so set `require_parameters: true` and validate every response with pydantic, plus one retry.
  - Writing in rioplatense Spanish and imitating the creator's voice may be weaker than Sonnet. We'll check this on real accounts.
- **Plan:** set the model per role with environment variables (`AI_LABEL_MODEL`, `AI_WRITER_MODEL`), and use OpenRouter's fallback list (`models: [primary, fallback]`) with a Claude Haiku-class model as the fallback. Switching models then needs no code change.
- Sources: [OpenRouter: DeepSeek V4.1 Flash](https://openrouter.ai/deepseek/deepseek-v4.1-flash) · [OpenRouter: DeepSeek V4 Flash 0731](https://openrouter.ai/deepseek/deepseek-v4-flash-0731) · [computeprices tracker](https://computeprices.com/providers/openrouter/models/deepseek-v4-flash).

## 6. Libraries (runtime, no torch)

pandas · numpy · scipy (Mann-Whitney U, bootstrap) · scikit-learn (ridge / HistGradientBoosting / permutation importance) · pydantic (schemas; the contract models already exist) · `openai` SDK or `httpx` for OpenRouter · pytest + mocked LLM responses.
Offline only (Colab Pro): pysentimiento (label validation), notebooks for the ENCC personas and model evaluation.

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| LLM down or slow during the demo | Timeouts + `FakeAnalyzer` template fallback with the same stats; pre-computed demo report (`DEMO_MODE`) |
| Invented numbers in insights | Numbers come only from the evidence JSON + the code-side number check |
| Overfitting or noise with ~40–200 posts | Minimum segment size, CIs, significance filter, honest `confidence`; the model is used for ranking, not as an oracle |
| Topic and time confounded | Multivariate model (§4.3 step 3) |
| Accounts with few posts / no impressions | `AnalysisError` with an es-AR message below a minimum (e.g. fewer than 20 scorable posts), or a reduced report |
| Structured output not supported by a routed endpoint | `require_parameters: true` + pydantic validation + one retry |

## 8. Validation plan with real data

1. Mark gives us 3–5 real `AccountSnapshot`s (public Argentine creators), saved as private test fixtures, never committed if they contain personal data.
2. Colab notebook: run P1–P4 on them, check pairwise accuracy, and inspect the labels against pysentimiento.
3. Read the generated insights on real accounts. Do they say something a creator didn't know?

## 9. Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Approach: **B (hybrid)**. B+ (agentic insight step) only if time allows | **agreed** (2026-10-30) |
| D2 | Score = **(c) geometric mean of relative ER and relative reach** (§4.2) | **agreed** |
| D3 | Topic method: LLM two-pass labeling with a **per-account taxonomy** (5–8 topics + `otros`, schema enum) | **agreed** |
| D4 | Pattern model: **ridge** on log(score) + bootstrap CIs, behind a swappable interface; Colab bake-off later. It is **fitted per account at analysis time** (milliseconds, no pre-training). It is **not a blocker**: the pipeline first ships with segment stats + tests, and ridge plugs into step P4 afterwards without changing the output contract | **agreed** |
| D5 | Models: a cheap model for every role, **DeepSeek V4.1 Flash** first, with a Claude Haiku-class fallback; configurable per role via env vars | **agreed**: get it working first, tune models later |
| D6 | Provider: **OpenRouter** behind an `LLMClient` interface | **agreed** |
| D7 | Analyze **originals + quotes**, **older than 48 h**, with a minimum of **~20 scorable posts**. Below the minimum, **no report** (`AnalysisError` with an es-AR message): better no analysis than a wrong one | **agreed** |
| D8 | Work mode: **pair programming in one session** for now; maybe split into two developers later | **agreed** |
| D9 | Extra labels in the same labeling call: **hook** (how the post opens) and **CTA** (what it asks the reader to do). Needs an additive contract change (v1.1.0) | **agreed**; contract change in plan stage 00 |

## 10. Proposals pending confirmation

### D4: the ML model, in detail

**Main model: regularized linear regression (`RidgeCV`) on `log(score)`.**
- **Features (one-hot / binary):** topic, tone, media type, length bucket, hour block (morning 6–12, midday 12–15, afternoon 15–19, night 19–24, late 0–6), weekend, has link, is question, has emoji, hashtag count (0 / 1 / 2+), matches trend, plus the hook and CTA labels if we add them.
- **Why ridge:**
  - With 40–200 rows it is stable where trees overfit.
  - It trains in milliseconds and needs no torch.
  - **Each coefficient reads directly as an effect:** exp(β) = multiplier on the score. For example, β = 0.30 for "foto" means photos rate about 1.35x, other things equal. That makes it easy to turn into an insight, and it adjusts for confounding (topic vs hour).
- **Confidence:** bootstrap the fit (resample the posts ~200 times) to get a confidence interval for each effect. An effect becomes an insight only if its CI excludes 0 and it has n ≥ 3 posts. That fills `Insight.confidence` honestly.
- **Evaluation:** cross-validated **pairwise accuracy**, i.e. the share of held-out post pairs ranked in the right order. Chance is 50%. This is the number for the pitch.
- **Comparison in Colab (not at runtime unless it wins clearly):** `HistGradientBoostingRegressor` + permutation importance. Keep it only if its pairwise accuracy beats ridge by a clear margin on real accounts.
- **Reuse:** the same fitted model scores the generated drafts (`Draft.estimated_score`), which closes the generation loop.
- **Optional per account:** fit it only when there is enough data, e.g. **at least ~30 scorable posts** and at least ~3 posts per feature level used. Otherwise skip it. The report then relies on segment stats alone, with lower confidence values, and drafts get `estimated_score = None` (or a segment-based estimate). The output contract is identical either way.

### D4 (continued): what ridge is, and the other options

**Ridge, in one paragraph.** Linear regression assumes every feature *adds a fixed amount* to log(score). For example, "photo: +0.30", "night: +0.20", "tarjetas: −0.50". A post's predicted score is the sum of its features' amounts. With few posts, plain linear regression over-reacts: three lucky posts at 9 am give "9 am" a huge coefficient. **Ridge adds a penalty on big coefficients**, so an effect only grows large if many posts support it. It works like a *skepticism dial* (`alpha`), and `RidgeCV` picks the dial automatically by cross-validation. The result: the same readable "+X% when…" effects, but far fewer invented ones.

**Options that fit small data (all in scikit-learn unless noted, all fast):**

| Model | What it adds | Downsides with 40–200 posts | Role |
|---|---|---|---|
| Plain linear regression (OLS) | Simplest | Unstable, inflated effects | No |
| **Ridge (L2)** | Stable, readable multipliers, adjusts for confounding | Keeps every feature (small effects stay small but nonzero) | **Default** |
| Lasso / ElasticNet (L1) | **Sets weak features to exactly 0**, so it does automatic feature selection and gives fewer, cleaner insights | Selection jumps around between resamples with little data | Compare |
| BayesianRidge | Like ridge, but returns **uncertainty natively** (no bootstrap needed) | Slightly less familiar | Compare (cheap swap) |
| HuberRegressor (robust) | Down-weights viral outliers instead of letting them dominate | Effects a bit harder to explain | Compare |
| **Pairwise ranking** (logistic regression on *differences* between two posts' features) | Optimizes exactly what we evaluate ("which of two posts did better"). n posts give ~n²/2 training pairs, so **more signal from small data** | Coefficients are "odds of beating another post": explainable, but less direct | **Strong alternative** |
| Random forest / gradient boosting (HistGB, LightGBM, XGBoost) + permutation importance or SHAP | Captures **interactions** (e.g. photos work only at night) | Overfits with fewer than ~300 posts, needs SHAP to explain, more tuning | Compare; use if the data is big |
| Text embeddings + ridge | Captures content beyond our labels | Not explainable as insights; embedding API call | Better used for "find similar top posts" in generation |
| No model: segment stats + tests only | Simplest | Can't separate confounded effects (topic vs hour) | Already in the fake; fallback |
| **Global model across many creators** (mixed effects / pooling, then per-account adjustment) | Learns from everyone: the long-term moat and the "aprende con el tiempo" story | Needs data from many accounts | **Roadmap / pitch**, not the hackathon |

**Proposal:** build the pattern engine behind one small interface (`fit(features, scores)` → effects + CIs + `predict`), with ridge as the default. A **model bake-off** in a Colab notebook compares ridge, ElasticNet, BayesianRidge, Huber, pairwise logistic and HistGB on real accounts, using cross-validated **pairwise accuracy**. If another model clearly wins, swapping it in is one line, since they share the scikit-learn API.

### D3: topics per account (recommended)

- **Recommended: per-account topics.** A fixed global list is too coarse for niche creators: "finanzas" doesn't tell a finance creator anything, while "presupuesto" vs "inversiones" does.
- **Guardrails:**
  - 5–8 topics per account, as short Spanish labels (1–3 words), plus `otros`.
  - The taxonomy pass sees a sample of up to ~60 posts. The assignment pass must choose from the list, which the JSON schema enforces with an enum.
- **Future (not now):** map each account topic to a broad global category, so we can benchmark against similar accounts. That would need an extra contract field.

## Sources

- Claude models and pricing: Anthropic API reference (Claude API skill, cached 2026-10-06).
- OpenRouter: [Structured outputs](https://openrouter.ai/docs/structured-outputs) · [Prompt caching](https://openrouter.ai/docs/features/prompt-caching) · [Embedding models](https://openrouter.ai/models/intfloat/multilingual-e5-large).
- Engagement prediction: [Emotional + temporal features with gradient boosting (arXiv 2508.21650)](https://arxiv.org/pdf/2508.21650) · [Can LLMs simulate social media engagement? (arXiv 2502.12073)](https://arxiv.org/html/2502.12073) · [AIMultiple: LLM audience simulation benchmark](https://research.aimultiple.com/audience-simulation) (many LLMs near chance).
- Spanish NLP: [pysentimiento (arXiv 2106.09462)](https://arxiv.org/pdf/2106.09462) · [RoBERTuito (arXiv 2111.09453)](https://arxiv.org/pdf/2111.09453) · [robertuito-sentiment model card](https://huggingface.co/pysentimiento/robertuito-sentiment-analysis/blob/a67a88f0b348b80b7194d86c6801f03ba24d5d84/README.md).
- Topic modeling on short texts: [Topic modeling for short texts with LLMs (arXiv 2406.00697)](https://arxiv.org/html/2406.00697v1) · [LLMs as an alternative to topic modelling (arXiv 2403.16248)](https://arxiv.org/pdf/2403.16248) · [LLM labels on BERTopic (arXiv 2502.18469)](https://arxiv.org/pdf/2502.18469v1) · [BERTopic on short Hindi texts (IndoNLP 2025)](https://aclanthology.org/2025.indonlp-1.3).
- X algorithm signals: see `docs/validation.md` §4.
