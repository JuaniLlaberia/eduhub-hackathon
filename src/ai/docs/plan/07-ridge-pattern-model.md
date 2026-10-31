# Stage 07: Ridge pattern model (optional per account)

- **Status:** done
- **Priority:** MUST (quality upgrade, not a blocker)
- **Depends on:** 06

## Goal

A per-account ridge regression on `log(score)` that estimates **adjusted effects** ("+35% con foto, a igualdad de lo demás") with **bootstrap CIs**. It feeds those effects into the insight evidence and confidence, and exposes `predict()` for scoring drafts (stage 08). It's **skipped automatically** when the account lacks data. The report contract doesn't change.

## Read first

- `../research.md` §10 D4 (what ridge is, the alternatives, the data-sufficiency rule)
- Handoff notes of stages 04–06 (where `EvidencePack.pattern_effects` and the analyzer hook live)

## Design

- **Dependency:** `scikit-learn`.
- **`patterns/base.py`:**
  - `class PatternModel(Protocol)`: `fit(rows: list[FeatureRow], scores: list[float]) -> None`, `effects() -> list[Effect]`, `predict(row: FeatureRow) -> float`;
  - `Effect(feature, value, multiplier, ci_low, ci_high, n)`; and
  - `FeatureRow`, a dict of categorical/binary features built from `PostFeatures` (topic, tone, hook, cta, media type, length bucket, hour block, weekend, has link, is question, has emoji, hashtag bucket, matches trend).
- **`patterns/ridge.py`:** `RidgePatternModel(alphas=np.logspace(-2, 3, 20), n_bootstrap=200, seed=0)`:
  - one-hot via `DictVectorizer`; `RidgeCV` on `log(score)`;
  - `multiplier = exp(coef)`; and
  - bootstrap refits for the CIs (percentiles at 5% and 95%).
- **`patterns/evaluation.py`:** `pairwise_accuracy(model_factory, rows, scores, k=5, seed=0) -> float`: k-fold cross-validation. In each held-out fold, the share of pairs with a different true score that the model ranks correctly.
- **The sufficiency rule:** `can_fit(rows, scores) -> bool`, true when there are ≥ 30 scorable posts and at least 3 posts per feature level used. Rare levels are merged into `otros`, or the feature is dropped.
- **Integration:**
  - The analyzer runs the model only when `can_fit`.
  - Significant effects (CI excluding 1.0) go into `EvidencePack.pattern_effects` as formatted strings (e.g. `1,35x`), which the stage 05 grounding allows.
  - Effects can raise or lower insight `confidence`.
  - The model is **not** persisted or part of the contract. Stage 08 refits it from `report.posts` (features + scores are in the report; it takes milliseconds). Expose `fit_from_report(report) -> PatternModel | None` for that.

## Tests to write first (`src/ai/tests/test_stage_07_ridge.py`) → STOP for approval

- On synthetic data where "foto" truly multiplies the score by 1.5 (n=120, noise, seed), the effect for photo is about 1.5 (within ±0.2) and its CI excludes 1.0. A no-effect feature's CI includes 1.0.
- Confounding: "noche" and "presupuesto" are correlated, but only "presupuesto" has a true effect → ridge gives "presupuesto" the larger effect, while plain segment stats would credit both.
- `can_fit` is false with 20 posts. The analyzer then produces a valid report with no pattern effects (`check_analyzer` still passes).
- `pairwise_accuracy` is about 0.5 on pure noise and well above 0.6 on the synthetic effect data. It's deterministic with a seed.
- `predict` gives a higher score to a row with the positive-effect feature.
- The effect multipliers in the evidence pass the grounding check.

## Definition of done

- [x] Tests green, plus ruff and style (239 passed: shared + stages 01–07)
- [x] Fit + bootstrap takes under 2 s for 200 posts (log it): ~0.04 s on every account; logged by `fit_from_posts`
- [x] Record the pairwise accuracy on the fixture in the handoff notes (and on real accounts once available)
- [x] Commit `ai: stage 07 ridge pattern model`

## Handoff notes

- Built on 2026-10-31: `patterns/base.py` (`FeatureRow`, `Effect` (+ `baseline`, `significant`), `PatternModel`, `feature_row`, `FeaturePlan`/`plan_features`, `can_fit`), `patterns/ridge.py` (`RidgePatternModel`), `patterns/evaluation.py` (`pairwise_accuracy`), `patterns/integration.py` (`fit_from_posts`, `fit_from_report`, `effect_items`, `adjust_confidence`). Adds `scikit-learn`. The analyzer calls `pattern_model(posts)`; `build_evidence(..., pattern_effects=...)` is a new optional argument (stage 05 callers unchanged).
- Tests: `src/ai/tests/test_stage_07_ridge.py`, approved by Juan (code was written before approval at the developer's request).
- Decisions beyond the plan:
  - **Reference coding:** each categorical feature drops its most common level (the baseline; ties alphabetical), binary features are "sí" vs "no". So `exp(coef)` reads "foto 1,5x vs. solo texto, a igualdad de lo demás". Plain one-hot with an intercept would split the effect across levels (photo ≈ 1.2x instead of 1.5x). `Effect` gained `baseline`.
  - Rare levels (< 3 posts) merge into `otros` when the merged group has ≥ 3, else they encode as the baseline; features left with one level are dropped. `can_fit` = ≥ 30 posts and ≥ 1 usable feature.
  - Scores are floored at 0.05 before `log`. Bootstrap refits use `Ridge` at the alpha `RidgeCV` chose (fast, 200 refits), CI = 5th–95th percentiles.
  - Evidence: only effects with CI excluding 1.0, n ≥ 3 **and** |multiplier − 1| ≥ 0.1 (smaller ones print as "1,0x"). Ids `model:<feature>:<value>`. The writer prompt now explains `efectos_modelo`.
  - Confidence: a finding gains +0.1 when the model's effect for the same level agrees (significant, same direction) and loses 0.1 otherwise; findings without a matching effect (e.g. timing combos) are unchanged.
  - Model errors (`ValueError`/`ArithmeticError`) skip the model; they never fail the analysis.
- Measurements (template mode, i.e. **without** LLM labels; 2026-10-31 snapshots):

  | Account | Scorable | Pairwise accuracy (5-fold) | Top effects |
  |---|---|---|---|
  | fixture (synthetic story) | 39 | 0.92 | tema presupuesto 1,8x; mediodía 0,6x; tarjetas 0,6x |
  | bilinkis | 70 | 0.58 | mañana 1,4x; video 1,3x |
  | mercadolibre | 50 | 0.65 | solo texto 0,5x; con link 0,6x; largo medio 1,5x |
  | paulina_cocina | 164 | 0.63 | solo texto 0,4x; con link 0,6x; foto 0,7x |
  | valearvejita | 40 | 0.49 | none worth showing |

  Pitch line: "nuestro modelo acierta 6 de cada 10 comparaciones" on real accounts before semantic labels. Re-measure with real LLM labels (topic/tone/hook/CTA) in the real-model session; they should help most on content-driven accounts like valearvejita. Stage 10's bake-off compares other models.
