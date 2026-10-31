"""
Alternative pattern models for the bake-off (research §10 D4). They share RidgePatternModel's encoding, so
swapping the default is one line. They only rank (fit/predict); effects() is empty because only ridge's
coefficients are read as insights.
"""
import itertools
import math
from collections.abc import Callable
from typing import Any
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import BayesianRidge, ElasticNetCV, HuberRegressor, LogisticRegression
from eduhub_ai.patterns.base import Effect, FeaturePlan, FeatureRow, PatternModel, plan_features
from eduhub_ai.patterns.ridge import MIN_SCORE, RidgePatternModel

MAX_PAIRS = 20_000
PAIR_SEED = 0

class EncodedModel:
    """
    Shared plumbing: plan the features on fit, one-hot encode rows, and fall back to a constant column when no
    feature survives the plan.
    """
    def __init__(self) -> None:
        """
        Start unfitted.
        """
        self._plan: FeaturePlan | None = None
        self._vectorizer = DictVectorizer(sparse=False)

    def effects(self) -> list[Effect]:
        """
        No readable effects (ranking only).
        """
        return []

    def _fit_matrix(self, rows: list[FeatureRow]) -> np.ndarray:
        """
        Plan the features and encode the training rows.
        """
        self._plan = plan_features(rows)
        encoded = [self._plan.encode(row) for row in rows]
        if not any(encoded):
            encoded = [{"constant": 0.0} for _ in rows]
        return self._vectorizer.fit_transform(encoded)

    def _row_matrix(self, row: FeatureRow) -> np.ndarray:
        """
        Encode one row with the plan from fit.
        """
        if self._plan is None:
            raise RuntimeError(f"{type(self).__name__}.predict called before fit")
        return self._vectorizer.transform([self._plan.encode(row)])

class SklearnPatternModel(EncodedModel):
    """
    Any scikit-learn regressor on log(score).
    """
    def __init__(self, make_estimator: Callable[[], Any]) -> None:
        """
        Keep the factory that builds a fresh estimator on every fit.
        """
        super().__init__()
        self._make_estimator = make_estimator
        self._estimator: Any = None

    @classmethod
    def elasticnet(cls) -> SklearnPatternModel:
        """
        ElasticNet with the L1/L2 mix and strength chosen by cross-validation.
        """
        return cls(lambda: ElasticNetCV(l1_ratio=[0.2, 0.5, 0.8], cv=5, max_iter=5000))

    @classmethod
    def bayesian_ridge(cls) -> SklearnPatternModel:
        """
        Bayesian ridge (native uncertainty).
        """
        return cls(BayesianRidge)

    @classmethod
    def huber(cls) -> SklearnPatternModel:
        """
        Huber regression (down-weights viral outliers).
        """
        return cls(lambda: HuberRegressor(max_iter=1000))

    @classmethod
    def hist_gb(cls) -> SklearnPatternModel:
        """
        Small gradient-boosted trees (captures interactions; prone to overfit on little data).
        """
        return cls(lambda: HistGradientBoostingRegressor(max_depth=3, learning_rate=0.05, max_iter=200,
                                                         min_samples_leaf=5, random_state=0))

    def fit(self, rows: list[FeatureRow], scores: list[float]) -> None:
        """
        Fit a fresh estimator on log(score).
        """
        x = self._fit_matrix(rows)
        y = np.log(np.maximum(np.asarray(scores, dtype=float), MIN_SCORE))
        self._estimator = self._make_estimator().fit(x, y)

    def predict(self, row: FeatureRow) -> float:
        """
        Predicted score multiplier.
        """
        return float(math.exp(self._estimator.predict(self._row_matrix(row))[0]))

class PairwiseLogisticModel(EncodedModel):
    """
    Logistic regression on feature differences of post pairs ("which of the two did better"): it optimizes the
    ranking directly. predict returns exp(w·x), only meaningful for ordering.
    """
    def __init__(self, max_pairs: int = MAX_PAIRS, seed: int = PAIR_SEED) -> None:
        """
        Cap the number of training pairs (sampled with seed when there are more).
        """
        super().__init__()
        self.max_pairs = max_pairs
        self.seed = seed
        self._weights: np.ndarray | None = None

    def fit(self, rows: list[FeatureRow], scores: list[float]) -> None:
        """
        Fit on (x_i - x_j, score_i > score_j) for pairs with different scores, both orders.
        """
        x = self._fit_matrix(rows)
        pairs = [(i, j) for i, j in itertools.combinations(range(len(rows)), 2) if scores[i] != scores[j]]
        if len(pairs) > self.max_pairs:
            chosen = np.random.default_rng(self.seed).choice(len(pairs), size=self.max_pairs, replace=False)
            pairs = [pairs[k] for k in sorted(chosen)]
        if not pairs:
            self._weights = np.zeros(x.shape[1])
            return
        diffs = np.array([x[i] - x[j] for i, j in pairs])
        labels = np.array([scores[i] > scores[j] for i, j in pairs], dtype=int)
        model = LogisticRegression(fit_intercept=False, max_iter=2000)
        model.fit(np.vstack([diffs, -diffs]), np.concatenate([labels, 1 - labels]))
        self._weights = model.coef_[0]

    def predict(self, row: FeatureRow) -> float:
        """
        exp(w·x): higher means more likely to beat other posts.
        """
        if self._weights is None:
            raise RuntimeError("PairwiseLogisticModel.predict called before fit")
        return float(math.exp(float(self._row_matrix(row)[0] @ self._weights)))

BAKEOFF_MODELS: dict[str, Callable[[], PatternModel]] = {
    "ridge": lambda: RidgePatternModel(n_bootstrap=20),
    "elasticnet": SklearnPatternModel.elasticnet,
    "bayesian_ridge": SklearnPatternModel.bayesian_ridge,
    "huber": SklearnPatternModel.huber,
    "pairwise_logistic": PairwiseLogisticModel,
    "hist_gb": SklearnPatternModel.hist_gb,
}
