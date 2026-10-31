"""
RidgePatternModel: RidgeCV on log(score) over one-hot features (each level vs its baseline), so exp(coef) is a
score multiplier "a igualdad de lo demás". Bootstrap refits at the chosen alpha give the effects' 90% CIs.
"""
import math
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import Ridge, RidgeCV
from eduhub_ai.patterns.base import Effect, FeaturePlan, FeatureRow, plan_features

DEFAULT_ALPHAS = np.logspace(-2, 3, 20)
MIN_SCORE = 0.05
CI_PERCENTILES = (5, 95)

class RidgePatternModel:
    """
    Per-account ridge model of log(score). Fit, then read effects() or predict() rows.
    """
    def __init__(self, alphas: np.ndarray = DEFAULT_ALPHAS, n_bootstrap: int = 200, seed: int = 0) -> None:
        """
        Configure the alpha grid for RidgeCV, the number of bootstrap refits and the random seed.
        """
        self.alphas = alphas
        self.n_bootstrap = n_bootstrap
        self.seed = seed
        self._plan: FeaturePlan | None = None
        self._vectorizer = DictVectorizer(sparse=False)
        self._model: RidgeCV | None = None
        self._effects: list[Effect] = []

    def fit(self, rows: list[FeatureRow], scores: list[float]) -> None:
        """
        Fit RidgeCV on log(score) (scores floored at MIN_SCORE) and bootstrap the effect CIs.
        """
        self._plan = plan_features(rows)
        encoded = [self._plan.encode(row) for row in rows]
        y = np.log(np.maximum(np.asarray(scores, dtype=float), MIN_SCORE))
        if not any(encoded):
            encoded = [{"constant": 0.0} for _ in rows]
        x = self._vectorizer.fit_transform(encoded)
        self._model = RidgeCV(alphas=self.alphas).fit(x, y)
        intervals = self._bootstrap(x, y, float(self._model.alpha_))
        self._effects = self._build_effects(x, intervals)

    def effects(self) -> list[Effect]:
        """
        Every kept feature level's effect, largest first (by distance from 1.0 on a log scale).
        """
        return list(self._effects)

    def predict(self, row: FeatureRow) -> float:
        """
        Predicted score multiplier for row (exp of the predicted log score).
        """
        if self._model is None or self._plan is None:
            raise RuntimeError("RidgePatternModel.predict called before fit")
        x = self._vectorizer.transform([self._plan.encode(row)])
        return float(math.exp(self._model.predict(x)[0]))

    def _bootstrap(self, x: np.ndarray, y: np.ndarray, alpha: float) -> np.ndarray:
        """
        Coefficient percentiles (5%, 95%) over bootstrap refits of Ridge at the chosen alpha.
        """
        rng = np.random.default_rng(self.seed)
        coefs = np.empty((self.n_bootstrap, x.shape[1]))
        for i in range(self.n_bootstrap):
            sample = rng.integers(0, len(y), size=len(y))
            coefs[i] = Ridge(alpha=alpha).fit(x[sample], y[sample]).coef_
        return np.percentile(coefs, CI_PERCENTILES, axis=0)

    def _build_effects(self, x: np.ndarray, intervals: np.ndarray) -> list[Effect]:
        """
        Turn coefficients and their intervals into Effects (multipliers vs each feature's baseline).
        """
        assert self._model is not None and self._plan is not None
        effects = []
        for column, name in enumerate(self._vectorizer.get_feature_names_out()):
            feature, has_level, value = str(name).partition("=")
            if not has_level:
                continue
            effects.append(Effect(
                feature=feature,
                value=value,
                baseline=self._plan.baselines[feature],
                multiplier=float(math.exp(self._model.coef_[column])),
                ci_low=float(math.exp(intervals[0, column])),
                ci_high=float(math.exp(intervals[1, column])),
                n=int(x[:, column].sum()),
            ))
        return sorted(effects, key=lambda e: (-abs(math.log(e.multiplier)), e.feature, e.value))
