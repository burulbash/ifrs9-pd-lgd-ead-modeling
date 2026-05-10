from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
    roc_curve,
)


def compute_binary_metrics(
    y_true: np.ndarray,
    y_score: np.ndarray,
    include_probability_metrics: bool = True,
) -> dict[str, float]:
    y_true = np.asarray(y_true)
    y_score = np.asarray(y_score)

    if len(np.unique(y_true)) < 2:
        metrics = {
            "roc_auc": np.nan,
            "gini": np.nan,
            "ks": np.nan,
            "average_precision": np.nan,
        }
    else:
        auc = roc_auc_score(y_true, y_score)
        fpr, tpr, _ = roc_curve(y_true, y_score)

        metrics = {
            "roc_auc": float(auc),
            "gini": float(2 * auc - 1),
            "ks": float(np.max(tpr - fpr)),
            "average_precision": float(average_precision_score(y_true, y_score)),
        }

    if include_probability_metrics:
        metrics["brier_score"] = float(brier_score_loss(y_true, y_score))
        metrics["mean_predicted_pd"] = float(np.mean(y_score))
        metrics["observed_default_rate"] = float(np.mean(y_true))

    return metrics


def compute_regression_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sample_weight: np.ndarray | None = None,
) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)

    error = y_pred - y_true
    abs_error = np.abs(error)
    squared_error = error**2

    metrics = {
        "mae": float(np.mean(abs_error)),
        "rmse": float(np.sqrt(np.mean(squared_error))),
        "mean_actual": float(np.mean(y_true)),
        "mean_predicted": float(np.mean(y_pred)),
    }

    if sample_weight is not None:
        weights = np.asarray(sample_weight, dtype=float)
        metrics["weighted_mae"] = float(np.average(abs_error, weights=weights))
        metrics["weighted_rmse"] = float(np.sqrt(np.average(squared_error, weights=weights)))

    return metrics
