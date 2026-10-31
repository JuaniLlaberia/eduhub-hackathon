# Stage 10: Evaluation, bake-off and demo hardening

- **Status:** todo
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

- [ ] Bake-off table recorded; default model confirmed or swapped
- [ ] Demo report(s) delivered to the back team; template mode verified
- [ ] Pitch numbers written into `docs/validation.md` (repo-wide file: confirm with the developer)
- [ ] `ai` merged into `dev`, with all teams' tests green on `dev`

## Handoff notes

_(fill in when done)_
