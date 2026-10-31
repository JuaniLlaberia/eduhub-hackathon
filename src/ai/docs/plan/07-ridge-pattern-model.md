# Stage 07: Ridge pattern model (optional per account)

- **Status:** todo
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

- [ ] Tests green, plus ruff and style
- [ ] Fit + bootstrap takes under 2 s for 200 posts (log it)
- [ ] Record the pairwise accuracy on the fixture in the handoff notes (and on real accounts once available)
- [ ] Commit `ai: stage 07 ridge pattern model`

## Handoff notes

_(fill in when done)_
