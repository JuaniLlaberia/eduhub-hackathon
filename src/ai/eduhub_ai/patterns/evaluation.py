"""
Pairwise accuracy (the pitch number): in k-fold cross-validation, the share of held-out post pairs with
different true scores that the model puts in the right order. 0.5 is chance.
"""
from collections.abc import Callable
import numpy as np
from eduhub_ai.patterns.base import FeatureRow, PatternModel

def pairwise_accuracy(
    model_factory: Callable[[], PatternModel],
    rows: list[FeatureRow],
    scores: list[float],
    k: int = 5,
    seed: int = 0,
) -> float:
    """
    Cross-validated pairwise ranking accuracy; ties in the prediction count as half right.
    """
    order = np.random.default_rng(seed).permutation(len(rows))
    folds = np.array_split(order, k)
    correct = 0.0
    total = 0
    for fold in folds:
        held_out = set(fold.tolist())
        train = [i for i in order if i not in held_out]
        model = model_factory()
        model.fit([rows[i] for i in train], [scores[i] for i in train])
        predicted = {i: model.predict(rows[i]) for i in held_out}
        held = sorted(held_out)
        for a_index, a in enumerate(held):
            for b in held[a_index + 1:]:
                if scores[a] == scores[b]:
                    continue
                total += 1
                truth = scores[a] > scores[b]
                if predicted[a] == predicted[b]:
                    correct += 0.5
                elif (predicted[a] > predicted[b]) == truth:
                    correct += 1
    return correct / total if total else 0.5
