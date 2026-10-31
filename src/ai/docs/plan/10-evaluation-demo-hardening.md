# Stage 10: Evaluation, bake-off and demo hardening

- **Status:** mostly done (team items pending: label grading, pitch numbers, demo reports hand-off, merge into `dev`)
- **Priority:** MUST before the demo (Sat 31 Oct, 14:00)
- **Depends on:** 06 (07–09 if done)

## Goal

Prove the AI works on **real accounts**, get honest numbers for the pitch, and make sure the demo can't fail because of the AI.

## Read first

- `../research.md` §7 (risks), §8 (validation plan), §10 D4 (the bake-off)
- `docs/validation.md` §8 (jury Q&A: "¿qué parte funciona de verdad?")
- The handoff notes of every completed stage

## Tasks

1. **Real data:** get 3–5 real `AccountSnapshot` JSON files from Mark (public Argentine creators, plus the demo account). Store them in `src/ai/tests/data/real/`, **git-ignored** unless the developer decides otherwise (personal data). **The back team starts later**, so don't block on this. Until real snapshots exist, run tasks 2–5 on the shared fixture plus synthetic snapshots (e.g. a generator script with known effects), and re-run them on real data once it arrives.
   - **Available (back team, 2026-10-31, on `origin/backend`):** all validated against the contract, with impressions on every post. Use only the `.json` files. The `.report.json` files next to them come from the fake analyzer, so ignore them.
     - Demo: `src/backend/fixtures/bilinkis.json`. 190 posts (120 replies, 68 originals, 2 quotes) and 25 AR trends.
     - `src/backend/snapshots/valearvejita.json`: science outreach, 69k followers, 106 posts.
     - `src/backend/snapshots/paulina_cocina.json`: cooking and humor, 310k followers, 200 posts, lots of media.
     - `src/backend/snapshots/mercadolibre.json`: brand account (contrast), 228k followers, 200 posts (150 replies, mostly customer support).
   - Copy them into `src/ai/tests/data/real/`. Never import from `src/backend/`. For more accounts, send Mark handles (`python -m eduhub_backend.tools.snapshot <handles>`). Once the analyzer is ready, the back team re-runs the snapshot tool with `EDUHUB_FAKE_AI=0` to regenerate the demo reports.
2. **Colab bake-off notebook** (`src/ai/notebooks/model_bakeoff.ipynb`): cross-validated pairwise accuracy of ridge vs ElasticNet vs BayesianRidge vs Huber vs pairwise logistic vs HistGradientBoosting on each real account. Record the table in `../research.md` §10. Swap the default model only if another wins clearly and consistently.
3. **Label quality check:** for one account, compare the LLM sentiment with pysentimiento (Colab only), and skim 30 topic/hook/CTA labels by hand. Note the agreement rate.
4. **Text quality review with the developer:** read the insights and drafts for each real account. Does each insight say something the creator didn't know? Fix the prompts and record the changes.
5. **Latency and cost:** measure the full analysis per account (target under 60 s, about $0.005). If it's too slow: smaller label batches with more concurrency, or skip the taxonomy pass for accounts with fewer than 40 posts.
6. **Demo hardening:**
   - Pre-compute the demo account's report(s) and hand them to Mark for `DEMO_MODE` (as `AnalysisReport` JSON).
   - Verify template mode (`AI_ENABLE_LLM=0`) gives a presentable report for the demo account.
   - Verify behavior with a wrong or missing API key (template mode, no crash).
7. **Pitch numbers** for `docs/validation.md` §8: pairwise accuracy, labels agreement, cost per analysis, latency, and "what is real vs simulated".

## Tests

- No new frozen tests are required. Optional: a regression test that runs `check_analyzer` on each real snapshot with a scripted client (skipped if the data folder is absent).

## Definition of done

- [x] Bake-off table recorded; default model confirmed or swapped (ridge confirmed)
- [ ] Demo report(s) delivered to the back team; template mode verified (template mode verified; real reports for all 4 accounts are in `tests/data/real/reports/`, the developer hands them to Mark as a backup — the back team also regenerates them with `EDUHUB_FAKE_AI=0`)
- [ ] Pitch numbers written into `docs/validation.md` (repo-wide file: confirm with the developer) — deferred to the final research/validation stage before the presentation; the numbers are in these notes
- [ ] `ai` merged into `dev`, with all teams' tests green on `dev`

## Handoff notes

- 2026-10-31, built: `patterns/alternatives.py` (`SklearnPatternModel` for ElasticNet / BayesianRidge / Huber / HistGB, `PairwiseLogisticModel`, `BAKEOFF_MODELS`), `scripts/bakeoff.py` (offline, local instead of a Colab notebook: it runs in ~13 s), `scripts/analyze_accounts.py` (real-model run over every real snapshot: saves reports + `labels_review.md` to `tests/data/real/reports/`, git-ignored, and prints time / calls / tokens / cost). Tests: `src/ai/tests/test_stage_10_hardening.py`, approved by Juan.
- Hardening:
  - `OpenRouterClient` builds the SDK with `max_retries=0`: a timed-out call no longer waits twice before our own fallbacks run (worst case before: SDK retry × batch retry).
  - `OpenRouterClient.usage` keeps calls, failures, tokens and cost (requests `usage: {include: true}` so OpenRouter reports cost).
  - Verified: wrong API key (real OpenRouter 401s) → full template report in 0.9 s, 8 failed calls, no crash. Template mode (`AI_ENABLE_LLM=0`) on the demo account (bilinkis) → 4 grounded insights (mañana 1,9x vs. el resto, video 1,4x, foto 0,8x, tarde de semana 0,9x), summary and recommendations: presentable but thinner than with the LLM.
- Bake-off, **template mode** (no LLM labels), 5-fold pairwise accuracy, mean of 3 splits:

  | Account | Scored | ridge | elasticnet | bayesian_ridge | huber | pairwise_logistic | hist_gb |
  |---|---|---|---|---|---|---|---|
  | bilinkis | 70 | 0.585 | 0.566 | 0.586 | 0.564 | 0.567 | **0.605** |
  | mercadolibre | 50 | 0.641 | 0.612 | 0.650 | 0.671 | 0.610 | **0.675** |
  | paulina_cocina | 164 | 0.636 | 0.628 | 0.634 | 0.629 | **0.655** | 0.616 |
  | valearvejita | 40 | 0.493 | 0.466 | 0.493 | 0.471 | 0.517 | **0.541** |
  | mean | | 0.589 | 0.568 | 0.591 | 0.584 | 0.587 | 0.609 |

  No clear, consistent winner (hist_gb +0.02 on average but loses on the largest account) → **ridge stays the default** (also the only one with readable effects). Re-run with LLM labels after `analyze_accounts.py`.
- **Real-model evaluation** (`analyze_accounts.py`, 2026-10-31, DeepSeek V4.1 Flash via OpenRouter, label reasoning off, writer low, throughput routing):

  | Account | Posts | Scored | Labeled | Insights | Time | LLM calls | Failed | Tokens in / out | Cost |
  |---|---|---|---|---|---|---|---|---|---|
  | bilinkis (demo) | 190 | 70 | 100% | 6 | 26.8 s | 5 | 0 | 28,267 / 8,553 | $0.0124 |
  | mercadolibre | 200 | 50 | 100% | 6 | 25.3 s | 4 | 0 | 12,068 / 6,831 | $0.0078 |
  | paulina_cocina | 200 | 164 | 100% | 6 | 26.1 s | 9 | 0 | 32,982 / 13,830 | $0.0190 |
  | valearvejita | 106 | 40 | 100% | 6 | 15.2 s | 4 | 0 | 9,284 / 5,002 | $0.0064 |

  Every analysis is under the 60 s target; cost averages **$0.011** (target was ~$0.005: fast providers cost more, still about one cent).
- **Bake-off with LLM labels** (saved reports):

  | Account | Scored | ridge | elasticnet | bayesian_ridge | huber | pairwise_logistic | hist_gb |
  |---|---|---|---|---|---|---|---|
  | bilinkis | 70 | 0.571 | 0.538 | **0.574** | 0.533 | 0.538 | 0.571 |
  | mercadolibre | 50 | 0.738 | 0.747 | 0.726 | 0.753 | **0.756** | 0.727 |
  | paulina_cocina | 164 | 0.677 | 0.674 | 0.679 | **0.684** | 0.674 | 0.664 |
  | valearvejita | 40 | 0.562 | 0.472 | 0.553 | 0.560 | 0.524 | **0.565** |
  | mean | | **0.637** | 0.608 | 0.633 | 0.632 | 0.623 | 0.632 |

  **Decision: ridge stays the default** — best mean with labels, never far from the best per account, and the only model with readable effects. LLM labels lift ridge from 0.589 (template features) to **0.637** (+4.8 points); biggest gains on mercadolibre (0.64 → 0.74) and valearvejita (0.49 → 0.56). Pitch: "nuestro modelo ordena bien 64 de cada 100 pares de posts (el azar es 50)".
- Text review (developer + Claude): the insights are account-specific and non-obvious (valearvejita: política argentina 2,2x and tono opinión 2,6x; mercadolibre: Fórmula 1 5,8x, atención al cliente no tracciona; paulina_cocina: contenido de YouTube 0,4x, sin CTA 1,2x). Follow-up: timing insights built on 2-post slots ("lunes 17 h 7,7x en 2 posts") get a flat 0.5 confidence; give slot evidence a size-based confidence (and/or prefer hour-block findings) in a later pass.
- Pending (team):
  - **Label grading:** `tests/data/real/reports/labels_review.md` (30 sampled labels) is reviewed with the whole team later; a first skim looked right. Record the agreement rate here.
  - **Pitch numbers** go into `docs/validation.md` during the final research/validation stage (time, cost, labels coverage, pairwise accuracy 0.637 vs 0.5 chance, +4.8 points from LLM labels, what is real vs simulated).
  - **Demo reports** to Mark (backup for `DEMO_MODE`), and the **merge into `dev`** coordinated with him.
  - pysentimiento comparison skipped (torch; optional Colab).
